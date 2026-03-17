"""Shared app — base models, utilities, permissions, pagination, middleware."""
import uuid
from django.db import models


class BaseModel(models.Model):
    """Abstract base with UUID pk and timestamps."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TrilingualMixin(models.Model):
    """Mixin to add _si and _ta variants of the 'name' field."""
    name_en = models.CharField(max_length=200)
    name_si = models.CharField(max_length=200, blank=True, default="")
    name_ta = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        abstract = True

    def get_name(self, lang="en"):
        return getattr(self, f"name_{lang}", "") or self.name_en

    def __str__(self):
        return self.name_en
