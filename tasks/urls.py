from django.urls import path
from . import views

urlpatterns = [
    path("inbox/", views.task_inbox, name="task_inbox"),
]
