"""
Vendor / VMS / MSP models.
VMS integration hub, MSP client workflows, vendor scorecards,
subcontractor management, fee schedules, RPO workspaces.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class VMSIntegration(models.Model):
    """
    A VMS (Vendor Management System) integration configuration for a client.
    """

    class VMSPlatform(models.TextChoices):
        BEELINE = "beeline", "Beeline"
        FIELDGLASS = "fieldglass", "SAP Fieldglass"
        IQN = "iqn", "IQN / Coupa"
        PEOPLEFLUENT = "peoplefluent", "PeopleFluent"
        SHIFTWISE = "shiftwise", "ShiftWise"
        VNDLY = "vndly", "VNDLY"
        SIMPLYVMS = "simplyvms", "SimplyVMS"
        CUSTOM = "custom", "Custom / Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Setup"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ERROR = "error", "Integration Error"
        DISCONNECTED = "disconnected", "Disconnected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="vms_integrations"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vms_integrations",
    )
    platform = models.CharField(max_length=30, choices=VMSPlatform.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Credentials (should be stored encrypted in production)
    api_endpoint = models.URLField(blank=True)
    api_key_hint = models.CharField(max_length=50, blank=True)  # last 4 chars only
    vendor_id = models.CharField(max_length=100, blank=True)
    # Sync config
    sync_job_feeds = models.BooleanField(default=True)
    sync_submittals = models.BooleanField(default=True)
    sync_interviews = models.BooleanField(default=True)
    sync_timesheets = models.BooleanField(default=False)
    sync_invoices = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=50, blank=True)
    last_sync_error = models.TextField(blank=True)
    # MSP
    is_msp_managed = models.BooleanField(default=False)
    msp_name = models.CharField(max_length=200, blank=True)
    program_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vms_integration"
        ordering = ["platform"]

    def __str__(self):
        return f"{self.get_platform_display()} – {self.client_account}"


class VMSJobFeed(models.Model):
    """
    A job order ingested from a VMS feed.
    """

    class Status(models.TextChoices):
        NEW = "new", "New (Unprocessed)"
        MATCHED = "matched", "Matched to Job Order"
        ACTIVE = "active", "Active"
        FILLED = "filled", "Filled"
        CANCELLED = "cancelled", "Cancelled / Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        VMSIntegration, on_delete=models.CASCADE, related_name="job_feeds"
    )
    vms_job_id = models.CharField(max_length=200)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    raw_data = models.JSONField(default=dict)
    # Mapped to internal job order
    job_order = models.ForeignKey(
        "job_orders.JobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vms_feeds",
    )
    ingested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vms_job_feed"
        unique_together = [["integration", "vms_job_id"]]

    def __str__(self):
        return f"VMS Job {self.vms_job_id}: {self.title}"


class VendorScorecard(models.Model):
    """Performance scorecard for the agency as a vendor on an MSP program."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="vendor_scorecards"
    )
    integration = models.ForeignKey(
        VMSIntegration, on_delete=models.CASCADE, related_name="scorecards"
    )
    period_label = models.CharField(max_length=50)
    fill_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_to_submit_days = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    submittal_to_interview_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    offer_to_start_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quality_score = models.IntegerField(null=True, blank=True)
    compliance_score = models.IntegerField(null=True, blank=True)
    overall_rank = models.IntegerField(null=True, blank=True)
    total_vendors = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vms_vendor_scorecard"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Scorecard {self.period_label} – {self.integration}"


class SubcontractorPartner(models.Model):
    """
    A subcontractor agency or partner used for overflow, niche roles, or co-delivery.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active Partner"
        PROBATION = "probation", "On Probation"
        SUSPENDED = "suspended", "Suspended"
        BLACKLISTED = "blacklisted", "Blacklisted"
        INACTIVE = "inactive", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="subcontractor_partners"
    )
    partner_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    specializations = models.JSONField(default=list)
    geographies = models.JSONField(default=list)
    markup_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    agreement_url = models.URLField(blank=True)
    insurance_verified = models.BooleanField(default=False)
    compliance_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vms_subcontractor"
        ordering = ["partner_name"]

    def __str__(self):
        return f"{self.partner_name} ({self.get_status_display()})"
