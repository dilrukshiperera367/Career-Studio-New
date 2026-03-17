"""Taxonomy app — Global skill/title/location reference data."""

import uuid
from django.db import models


class SkillTaxonomy(models.Model):
    """Canonical skill definitions (global, not per-tenant)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_name = models.CharField(max_length=200, unique=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ("programming_language", "Programming Language"),
            ("framework", "Framework"),
            ("tool", "Tool"),
            ("platform", "Platform"),
            ("methodology", "Methodology"),
            ("soft_skill", "Soft Skill"),
            ("domain", "Domain"),
            ("certification", "Certification"),
            ("other", "Other"),
        ],
        default="other",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skill_taxonomy"
        verbose_name_plural = "Skill taxonomy"
        ordering = ["canonical_name"]

    def __str__(self):
        return self.canonical_name


class SkillAlias(models.Model):
    """Aliases for skills (case-insensitive matching)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill = models.ForeignKey(SkillTaxonomy, on_delete=models.CASCADE, related_name="aliases")
    alias_normalized = models.CharField(max_length=200, db_index=True)

    class Meta:
        db_table = "skill_aliases"
        unique_together = [("alias_normalized",)]

    def __str__(self):
        return f"{self.alias_normalized} → {self.skill.canonical_name}"


class TitleAlias(models.Model):
    """Normalize job titles to canonical forms."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_title = models.CharField(max_length=200)
    alias_normalized = models.CharField(max_length=200, unique=True, db_index=True)

    class Meta:
        db_table = "title_aliases"

    def __str__(self):
        return f"{self.alias_normalized} → {self.canonical_title}"


class LocationAlias(models.Model):
    """Normalize locations to structured city/country."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.CharField(max_length=200)
    country_code = models.CharField(max_length=5)
    alias_normalized = models.CharField(max_length=200, unique=True, db_index=True)

    class Meta:
        db_table = "location_aliases"

    def __str__(self):
        return f"{self.alias_normalized} → {self.city}, {self.country_code}"
