from django.shortcuts import render

from tasks.models import Task


def task_inbox(request):
    tasks = Task.objects.filter(status=Task.Status.TODO).order_by("-created_at")
    return render(request, "tasks/inbox.html", {"tasks": tasks})
