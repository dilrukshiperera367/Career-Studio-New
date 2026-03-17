"""Foreign Employment app — SLBFE overseas jobs, agencies, pre-departure info."""
import uuid
from django.db import models
from django.conf import settings


class ForeignEmploymentAgency(models.Model):
    """Licensed foreign employment agencies registered with SLBFE."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    name_si = models.CharField(max_length=200, blank=True, default="")
    name_ta = models.CharField(max_length=200, blank=True, default="")
    slug = models.SlugField(unique=True)
    license_number = models.CharField(max_length=50, unique=True)
    license_valid_until = models.DateField(null=True, blank=True)
    is_slbfe_registered = models.BooleanField(default=False)
    address = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    website = models.URLField(max_length=500, blank=True, default="")
    countries_served = models.JSONField(default=list, blank=True)
    specializations = models.JSONField(default=list, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_foreign_agencies"
        verbose_name_plural = "Foreign employment agencies"


class OverseasJob(models.Model):
    """Jobs posted for overseas employment."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(ForeignEmploymentAgency, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=200)
    title_si = models.CharField(max_length=200, blank=True, default="")
    title_ta = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField()
    description_si = models.TextField(blank=True, default="")
    description_ta = models.TextField(blank=True, default="")
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True, default="")
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="USD")
    contract_duration_months = models.IntegerField(null=True, blank=True)
    benefits = models.JSONField(default=list, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    vacancies = models.IntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    deadline = models.DateField(null=True, blank=True)
    slbfe_approval_no = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_overseas_jobs"
        ordering = ["-created_at"]


class PreDepartureChecklist(models.Model):
    """Pre-departure checklist items for overseas workers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    title_si = models.CharField(max_length=200, blank=True, default="")
    title_ta = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField()
    description_si = models.TextField(blank=True, default="")
    description_ta = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        db_table = "jf_predeparture_checklist"
        ordering = ["country", "sort_order"]
