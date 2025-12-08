from django.urls import path
from . import views

urlpatterns = [
    path("board/", views.task_board, name="task_board"),
    path("board/move/", views.move_task, name="task_move"),
    path("task/<int:task_id>/edit/", views.edit_task, name="edit_task"),
]
