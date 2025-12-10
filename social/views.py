from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from django.db.models import Count, Max, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.views import HttpRequest
from social.forms import ContactTouchpointForm
from social.models import Contact, ContactTouchpoint


@dataclass
class RelationshipStrength:
    label: str
    score: int
    state: str
    days_since: Optional[int]
    next_due_in: Optional[int]
    last_touchpoint: Optional[date]
    touchpoints_recent: int = 0
    overdue_by: Optional[int] = None


def contacts_dashboard(request: HttpRequest, slug: Optional[str] = None):
    contacts, today = _fetch_contacts_with_strength()
    active_slug = slug or request.GET.get("contact")
    active_contact = _find_contact(contacts, active_slug) or (contacts[0] if contacts else None)

    context = {
        "contacts": contacts,
        "active_contact": active_contact,
        "today": today,
    }
    if active_contact:
        context.update(_contact_detail_context(active_contact, today))

    return render(request, "social/contacts_dashboard.html", context)


def contact_detail(request: HttpRequest, slug: str):
    if not request.htmx:
        url = reverse("contacts_dashboard")
        return redirect(f"{url}?contact={slug}")

    contacts, today = _fetch_contacts_with_strength()
    contact = _find_contact(contacts, slug)
    if not contact:
        contact = get_object_or_404(Contact, slug=slug)
        contact.strength = _compute_strength(contact, today)

    context = {
        "contacts": contacts,
        "active_contact": contact,
        "today": today,
        **_contact_detail_context(contact, today),
    }
    return render(request, "social/partials/contact_detail.html", context)


def create_touchpoint(request: HttpRequest):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    contacts, today = _fetch_contacts_with_strength()
    contact_slug = request.POST.get("contact")
    active_contact = _find_contact(contacts, contact_slug)

    form = ContactTouchpointForm(request.POST, contact=active_contact)
    if form.is_valid():
        touchpoint = form.save()
        _update_last_contacted(touchpoint)
        contacts, today = _fetch_contacts_with_strength()
        active_contact = _find_contact(contacts, touchpoint.contact.slug)
        context = {
            "contacts": contacts,
            "active_contact": active_contact,
            "today": today,
            **_contact_detail_context(active_contact, today, form=ContactTouchpointForm(contact=active_contact), swap_contact_row=True, saved=True),
        }
        template = "social/partials/contact_detail.html" if request.htmx else "social/contacts_dashboard.html"
        return render(
            request,
            template,
            context,
            status=201,
        )

    context = {
        "contacts": contacts,
        "active_contact": active_contact,
        "today": today,
        **_contact_detail_context(active_contact, today, form=form),
    }
    template = "social/partials/contact_detail.html" if request.htmx else "social/contacts_dashboard.html"
    return render(request, template, context, status=400)


# Helpers
def _fetch_contacts_with_strength():
    today = timezone.localdate()
    ninety_days_ago = today - timedelta(days=90)
    contacts = list(
        Contact.objects.annotate(
            last_touchpoint=Max("contacttouchpoint__date"),
            touchpoints_recent=Count(
                "contacttouchpoint",
                filter=Q(contacttouchpoint__date__gte=ninety_days_ago),
            ),
        )
        .prefetch_related("interests")
        .order_by("name")
    )
    for contact in contacts:
        contact.strength = _compute_strength(contact, today)
    return contacts, today


def _find_contact(contacts: Iterable[Contact], slug: Optional[str]):
    if not slug:
        return None
    for contact in contacts:
        if str(contact.slug) == str(slug):
            return contact
    return None


def _compute_strength(contact: Contact, today):
    target_days = max(contact.check_in_frequency_days or 30, 1)
    last_date = getattr(contact, "last_touchpoint", None) or contact.last_contacted_at
    if last_date is None:
        last_date = (
            ContactTouchpoint.objects.filter(contact=contact).aggregate(Max("date")).get("date__max")
        )
    if last_date:
        days_since = (today - last_date).days
    else:
        days_since = None

    if days_since is None:
        label, state, score = "Cold start", "danger", 25
        next_due_in = target_days
    else:
        freshness_penalty = int((days_since / target_days) * 60)
        consistency_boost = min(10, (getattr(contact, "touchpoints_recent", 0) or 0) * 2)
        raw_score = 100 - freshness_penalty + consistency_boost
        score = max(5, min(100, raw_score))
        if days_since <= target_days * 0.5:
            label, state = "Strong", "success"
        elif days_since <= target_days:
            label, state = "Steady", "primary"
        elif days_since <= target_days * 1.5:
            label, state = "Needs touch", "warning"
        else:
            label, state = "At risk", "danger"
        next_due_in = target_days - days_since

    return RelationshipStrength(
        label=label,
        score=int(score),
        state=state,
        days_since=days_since,
        next_due_in=next_due_in,
        last_touchpoint=last_date,
        touchpoints_recent=getattr(contact, "touchpoints_recent", 0) or 0,
        overdue_by=abs(next_due_in) if next_due_in is not None and next_due_in < 0 else None,
    )


def _contact_detail_context(
    contact: Optional[Contact],
    today,
    *,
    form: Optional[ContactTouchpointForm] = None,
    swap_contact_row: bool = False,
    saved: bool = False,
):
    touchpoints = (
        ContactTouchpoint.objects.filter(contact=contact).order_by("-date", "-created_at")
        if contact
        else ContactTouchpoint.objects.none()
    )
    form = form or ContactTouchpointForm(contact=contact, initial={"date": today})
    return {
        "contact": contact,
        "touchpoints": touchpoints,
        "form": form,
        "today": today,
        "swap_contact_row": swap_contact_row,
        "saved": saved,
    }


def _update_last_contacted(touchpoint: ContactTouchpoint):
    contact = touchpoint.contact
    if not contact.last_contacted_at or touchpoint.date > contact.last_contacted_at:
        contact.last_contacted_at = touchpoint.date
        contact.save(update_fields=["last_contacted_at", "updated_at"])
