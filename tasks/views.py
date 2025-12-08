from typing import Dict, List
from datetime import timedelta

from django import forms
from django.db import models
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.views import HttpRequest
from tasks.models import Task
from tasks.models import Comment

BOARD_STATUSES = [
    (Task.Status.TODO, "To do"),
    (Task.Status.IN_PROGRESS, "In progress"),
    (Task.Status.BLOCKED, "Blocked"),
    (Task.Status.DONE, "Recently done"),
]


def task_board(request: HttpRequest):
    return render(request, "tasks/board.html", _fetch_board_context())


@require_POST
def move_task(request: HttpRequest):
    task_id = request.POST.get("task_id")
    status = request.POST.get("status")
    valid_statuses = {code for code, _ in BOARD_STATUSES}
    if not task_id or not status or status not in valid_statuses:
        return render(
            request,
            "tasks/partials/board.html",
            {**_fetch_board_context(), "error": "Invalid request."},
            status=400,
        )

    task = get_object_or_404(Task, pk=task_id)
    max_order = (
        Task.objects.filter(status=status).aggregate(max_order=models.Max("order"))[
            "max_order"
        ]
        or 0
    )
    task.status = status
    task.order = max_order + 1
    update_fields = ["status", "order", "updated_at"]
    if status == Task.Status.DONE and task.completed_at is None:
        task.completed_at = timezone.now()
        update_fields.append("completed_at")
    task.save(update_fields=update_fields)

    return render(
        request,
        "tasks/partials/board.html",
        {**_fetch_board_context(), "dropped_task_pk": task.pk},
    )


# Helper functions
def _fetch_board_context():
    cutoff = timezone.now() - timedelta(days=14)
    tasks = (
        Task.objects.filter(status__in=[code for code, _ in BOARD_STATUSES])
        .filter(
            models.Q(status=Task.Status.DONE, completed_at__gte=cutoff)
            | ~models.Q(status=Task.Status.DONE)
        )
        .select_related("parent")
        .prefetch_related("tags")
        .order_by("order", "-priority", "due_at", "-created_at")
    )
    grouped: Dict[Task.Status | str, List[Task]] = {
        code: [] for code, _ in BOARD_STATUSES
    }
    for task in tasks:
        grouped[task.status].append(task)

    columns = [
        {"code": code, "label": label, "tasks": grouped.get(code, [])}
        for code, label in BOARD_STATUSES
    ]
    return {"columns": columns}


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "status",
            "priority",
            "energy",
            "due_at",
            "estimate_minutes",
            "parent",
            "tags",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Details"}
            ),
            "due_at": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "estimate_minutes": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ["status", "priority", "energy", "parent", "tags"]:
            widget = self.fields[name].widget
            css = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{css} form-select".strip()


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Add a comment...",
                }
            )
        }


def edit_task(request: HttpRequest, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    comment_form = CommentForm()

    if request.method == "POST":
        # If the POST is for comments
        if "content" in request.POST and "title" not in request.POST:
            comment_form = CommentForm(request.POST)
            form = TaskForm(instance=task)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.task = task
                comment.save()
                if request.htmx:
                    return render(
                        request,
                        "tasks/partials/task_comments.html",
                        {"task": task, "comment_form": CommentForm()},
                    )
                return redirect("edit_task", task_id=task.pk)
        else:
            form = TaskForm(request.POST, instance=task)
            if form.is_valid():
                form.save()
                if request.htmx:
                    return render(
                        request,
                        "tasks/partials/task_form_card.html",
                        {
                            "form": form,
                            "task": task,
                            "saved": True,
                            "comment_form": comment_form,
                        },
                    )
                return redirect("task_board")
    else:
        form = TaskForm(instance=task)

    template = (
        "tasks/partials/task_form_card.html" if request.htmx else "tasks/task_edit.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "task": task,
            "saved": False,
            "comment_form": comment_form,
        },
        status=400 if form.errors else 200,
    )
