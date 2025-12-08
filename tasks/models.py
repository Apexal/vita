from django.db import models
from django.utils import timezone
from core.models import TimestampedModel


class Tag(TimestampedModel):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Optional hex color for UI accents.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Project(TimestampedModel):
    tags = models.ManyToManyField("Tag", related_name="projects", blank=True)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Task(TimestampedModel):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        CANCELLED = "cancelled", "Cancelled"
        DONE = "done", "Done"

    class Priority(models.IntegerChoices):
        LOW = 1, "Low"
        NORMAL = 2, "Normal"
        HIGH = 3, "High"
        URGENT = 4, "Urgent"

    class Energy(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    # Scheduling / planning
    due_at = models.DateField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    estimate_minutes = models.PositiveSmallIntegerField(null=True, blank=True)

    energy = models.CharField(
        max_length=8,
        choices=Energy.choices,
        default=Energy.MEDIUM,
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subtasks",
    )
    tags = models.ManyToManyField("Tag", related_name="tasks", blank=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Manual ordering within a list.",
    )

    class Meta:
        ordering = ["status", "-priority", "due_at", "order", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["due_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def cancel(self) -> None:
        self.status = Task.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    def mark_done(self) -> None:
        self.status = Task.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    @property
    def is_subtask(self) -> bool:
        return self.parent is not None

    @property
    def has_subtasks(self) -> bool:
        return self.subtasks.exists()

    @property
    def is_active(self) -> bool:
        return self.status not in {Task.Status.DONE, Task.Status.CANCELLED}

    @property
    def is_overdue(self) -> bool:
        return (
            self.status != Task.Status.DONE
            and self.due_at is not None
            and self.due_at < timezone.now()
        )


class Comment(TimestampedModel):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    content = models.TextField()

    def __str__(self) -> str:
        return self.content
