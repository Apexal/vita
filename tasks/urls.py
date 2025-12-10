from django.urls import path
from . import views

urlpatterns = [
    path("board/", views.task_board, name="task_board"),
    path("board/fragment/", views.board_fragment, name="task_board_fragment"),
    path("board/move/", views.move_task, name="task_move"),
    path("add/", views.create_task, name="task_add"),
    path("tasks/", views.task_list, name="task_list"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/add/", views.create_project, name="project_add"),
    path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
    path("tags/", views.tag_list, name="tag_list"),
    path("tags/add/", views.create_tag, name="tag_add"),
    path("tags/<int:tag_id>/", views.tag_detail, name="tag_detail"),
    path("task/<int:task_id>/edit/", views.edit_task, name="edit_task"),
]
