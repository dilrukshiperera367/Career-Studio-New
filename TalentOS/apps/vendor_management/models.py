"""Vendor Management app — Staffing agency relationships, fee schedules, and scorecards."""

import uuid
from django.db import models


class VendorAgency(models.Model):
    """An external staffing/recruiting agency or RPO partner."""

    TIER_CHOICES = [
        ("preferred", "Preferred"),
        ("approved", "Approved"),
        ("probationary", "Probationary"),
        ("inactive", "Inactive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="vendor_agencies")
    name = models.CharField(max_length=255)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="approved")
    website = models.URLField(blank=True, default="")
    specialties = models.JSONField(
        default=list, blank=True,
        help_text='["Engineering", "Finance", "Executive Search"]'
    )
    regions = models.JSONField(default=list, blank=True, help_text="Geographies this agency covers")
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    nda_signed = models.BooleanField(default=False)
    msa_document_url = models.URLField(blank=True, default="", help_text="Master Service Agreement URL")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_agencies"
        ordering = ["tier", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"


class VendorContact(models.Model):
    """A named point of contact at a vendor agency."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="vendor_contacts")
    agency = models.ForeignKey(VendorAgency, on_delete=models.CASCADE, related_name="contacts")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True, default="")
    title = models.CharField(max_length=150, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vendor_contacts"
        ordering = ["agency", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} @ {self.agency.name}"


class VendorAccess(models.Model):
    """Controls which jobs a vendor agency can see and submit candidates for."""

    ACCESS_LEVEL_CHOICES = [
        ("view_only", "View Only"),
        ("can_submit", "Can Submit"),
        ("exclusive", "Exclusive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="vendor_access_grants")
    agency = models.ForeignKey(VendorAgency, on_delete=models.CASCADE, related_name="access_grants")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="vendor_access_grants")
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVEL_CHOICES, default="can_submit")
    granted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="vendor_access_grants_given"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vendor_access_grants"
        unique_together = [("agency", "job")]

    def __str__(self):
        return f"{self.agency.name} → {self.job.title} ({self.access_level})"


class FeeSchedule(models.Model):
    """The placement fee terms for an agency–tenant engagement."""

    FEE_TYPE_CHOICES = [
        ("percent_base", "% of Base Salary"),
        ("fixed", "Fixed Fee"),
        ("retained", "Retained Search"),
        ("container", "Container / Milestone"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="fee_schedules")
    agency = models.ForeignKey(VendorAgency, on_delete=models.CASCADE, related_name="fee_schedules")
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, default="percent_base")
    fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Used when fee_type=percent_base"
    )
    fixed_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    guarantee_days = models.IntegerField(
        default=90, help_text="Days the placement is guaranteed; refund/replacement on exit"
    )
    applies_to_levels = models.JSONField(default=list, blank=True, help_text="Job levels this fee applies to")
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fee_schedules"
        ordering = ["agency", "-effective_date"]

    def __str__(self):
        return f"{self.agency.name} — {self.get_fee_type_display()}"


class CandidateOwnershipRule(models.Model):
    """Defines how long a vendor 'owns' a submitted candidate to prevent double-billing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="ownership_rules")
    agency = models.ForeignKey(VendorAgency, on_delete=models.CASCADE, related_name="ownership_rules")
    ownership_days = models.IntegerField(
        default=180, help_text="Days vendor retains claim on a submitted candidate"
    )
    applies_across_jobs = models.BooleanField(
        default=True, help_text="True = ownership applies to any role, False = job-specific"
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_ownership_rules"
        unique_together = [("tenant", "agency")]

    def __str__(self):
        return f"{self.agency.name} — {self.ownership_days}d ownership"


class VendorScorecard(models.Model):
    """Periodic performance scorecard for a vendor agency."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="vendor_scorecards")
    agency = models.ForeignKey(VendorAgency, on_delete=models.CASCADE, related_name="scorecards")
    period_start = models.DateField()
    period_end = models.DateField()
    submissions_count = models.IntegerField(default=0)
    interviews_count = models.IntegerField(default=0)
    offers_count = models.IntegerField(default=0)
    hires_count = models.IntegerField(default=0)
    avg_time_to_submit_days = models.FloatField(null=True, blank=True)
    quality_score = models.FloatField(null=True, blank=True, help_text="0–100 overall quality rating")
    diversity_hire_rate = models.FloatField(null=True, blank=True, help_text="% hires from underrepresented groups")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vendor_scorecards"
        ordering = ["agency", "-period_start"]

    def __str__(self):
        return f"{self.agency.name} scorecard {self.period_start}–{self.period_end}"


class VendorSLA(models.Model):
    """Service level agreement terms between a vendor and the tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="vendor_slas")
    agency = models.ForeignKey(VendorAgency, on_delete=models.CASCADE, related_name="slas")
    max_time_to_submit_days = models.IntegerField(default=5)
    min_submissions_per_week = models.IntegerField(default=2)
    max_rejection_rate_percent = models.FloatField(default=50.0)
    breach_escalation_contact = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vendor_sla_escalations"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_slas"
        unique_together = [("tenant", "agency")]

    def __str__(self):
        return f"SLA — {self.agency.name}"


class VendorSubmission(models.Model):
    """A candidate formally submitted by a vendor for a job."""

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("reviewing", "Reviewing"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("duplicate", "Duplicate"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="vendor_submissions")
    agency = models.ForeignKey(VendorAgency, on_delete=models.CASCADE, related_name="submissions")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="vendor_submissions")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vendor_submissions"
    )
    vendor_candidate_name = models.CharField(max_length=255, blank=True, default="")
    vendor_candidate_email = models.EmailField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    resume_url = models.URLField(blank=True, default="")
    vendor_notes = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_vendor_submissions"
    )

    class Meta:
        db_table = "vendor_submissions"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["agency", "job"]),
        ]

    def __str__(self):
        return f"{self.vendor_candidate_name or 'Unknown'} submitted by {self.agency.name}"
