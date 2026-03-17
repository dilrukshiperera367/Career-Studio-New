"""Taxonomy app — Districts, Provinces, Categories, Industries, Skills, Education Levels.
Features #58–60: Trilingual taxonomies.
"""
from django.db import models
from apps.shared.models import TrilingualMixin


class Province(TrilingualMixin, models.Model):
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = "jf_provinces"
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en


class District(TrilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="districts")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "jf_districts"
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en


class JobCategory(TrilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, default="briefcase")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    sort_order = models.IntegerField(default=0)
    job_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "jf_job_categories"
        ordering = ["sort_order", "name_en"]
        verbose_name_plural = "Job categories"


class JobSubCategory(TrilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, related_name="subcategories")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "jf_job_subcategories"
        ordering = ["sort_order", "name_en"]
        verbose_name_plural = "Job subcategories"


class Industry(TrilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    naics_code = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "jf_industries"
        ordering = ["name_en"]
        verbose_name_plural = "Industries"


class Skill(models.Model):
    name_en = models.CharField(max_length=100)
    name_si = models.CharField(max_length=100, blank=True, default="")
    name_ta = models.CharField(max_length=100, blank=True, default="")
    slug = models.SlugField(unique=True)
    canonical_name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=50,
        choices=[
            ("programming", "Programming"),
            ("framework", "Framework"),
            ("database", "Database"),
            ("devops", "DevOps"),
            ("design", "Design"),
            ("soft_skill", "Soft Skill"),
            ("language", "Language"),
            ("trade", "Trade"),
            ("certification", "Certification"),
            ("other", "Other"),
        ],
        default="other",
    )
    aliases = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "jf_skills"
        ordering = ["canonical_name"]

    def __str__(self):
        return self.canonical_name


class EducationLevel(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name_en = models.CharField(max_length=100)
    name_si = models.CharField(max_length=100, blank=True, default="")
    name_ta = models.CharField(max_length=100, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_sl_specific = models.BooleanField(default=False)

    class Meta:
        db_table = "jf_education_levels"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name_en
