from django.urls import path

from social import views

urlpatterns = [
    path("relationships/", views.contacts_dashboard, name="contacts_dashboard"),
    path(
        "relationships/contact/<slug:slug>/",
        views.contact_detail,
        name="contact_detail",
    ),
    path("relationships/touchpoints/add/", views.create_touchpoint, name="touchpoint_add"),
]
