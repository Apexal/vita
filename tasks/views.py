from typing import Dict, List
from django.db import models
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from core.views import HttpRequest
from tasks.models import Task

BOARD_STATUSES = [
    (Task.Status.TODO, "To do"),
    (Task.Status.IN_PROGRESS, "In progress"),
    (Task.Status.BLOCKED, "Blocked"),
    (Task.Status.DONE, "Done"),
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
    task.save(update_fields=["status", "order", "updated_at"])

    return render(request, "tasks/partials/board.html", _fetch_board_context())


# Helper functions
def _fetch_board_context():
    tasks = (
        Task.objects.filter(status__in=[code for code, _ in BOARD_STATUSES])
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
