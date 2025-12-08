from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the record was last updated.",
    )

    class Meta:
        abstract = True
