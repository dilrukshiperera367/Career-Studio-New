"""CampusOS — Shared abstract base models."""

import uuid
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class CampusOwnedModel(UUIDModel, TimestampedModel):
    """Base for models scoped to a campus."""

    campus = models.ForeignKey(
        "campus.Campus",
        on_delete=models.CASCADE,
        related_name="+",
    )

    class Meta:
        abstract = True
