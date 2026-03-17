"""Consent & Privacy — GDPR/CCPA compliance, data rights, privacy settings.
Models: ConsentRecord, DataExportRequest, DataDeletionRequest, PrivacySetting.
"""
import uuid
from django.db import models
from django.conf import settings


# ── Consent Records ───────────────────────────────────────────────────────────

class ConsentRecord(models.Model):
    """Tracks user consent for specific data processing activities."""

    class ConsentType(models.TextChoices):
        PROFILE_PROCESSING = "profile_processing", "Profile Data Processing"
        JOB_MATCHING = "job_matching", "AI Job Matching"
        ANALYTICS = "analytics", "Analytics & Insights"
        MARKETING = "marketing", "Marketing Communications"
        THIRD_PARTY_SHARING = "third_party", "Third-Party Data Sharing"
        EMPLOYER_VISIBILITY = "employer_visibility", "Profile Visible to Employers"
        AI_SCREENING = "ai_screening", "AI-Assisted Screening"
        COOKIE_TRACKING = "cookies", "Cookie & Tracking"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="consent_records"
    )
    consent_type = models.CharField(max_length=30, choices=ConsentType.choices)
    is_granted = models.BooleanField(default=False)
    version = models.CharField(max_length=20, default="1.0", help_text="Policy version at time of consent")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cx_consent_record"
        ordering = ["-created_at"]
        unique_together = ["user", "consent_type", "version"]

    def __str__(self):
        status = "Granted" if self.is_granted else "Revoked"
        return f"{self.user} — {self.get_consent_type_display()} ({status})"


# ── Data Export Requests ──────────────────────────────────────────────────────

class DataExportRequest(models.Model):
    """GDPR/CCPA data portability request."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready for Download"
        DOWNLOADED = "downloaded", "Downloaded"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="data_export_requests"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    format = models.CharField(max_length=10, default="json", help_text="json, csv, or zip")
    file_url = models.URLField(blank=True, default="")
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "cx_data_export_request"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Export {self.id} — {self.user} ({self.get_status_display()})"


# ── Data Deletion Requests ────────────────────────────────────────────────────

class DataDeletionRequest(models.Model):
    """Right to be forgotten / data deletion request."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        PROCESSING = "processing", "Processing Deletion"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    class Scope(models.TextChoices):
        FULL = "full", "Full Account Deletion"
        PROFILE = "profile", "Profile Data Only"
        APPLICATIONS = "applications", "Application History"
        AI_DATA = "ai_data", "AI/ML Training Data"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="data_deletion_requests"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.FULL)
    reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reviewed_deletions"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    retention_note = models.TextField(
        blank=True, default="",
        help_text="Legal reason if any data must be retained"
    )

    class Meta:
        db_table = "cx_data_deletion_request"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Delete {self.id} — {self.user} ({self.get_scope_display()})"


# ── Privacy Settings ──────────────────────────────────────────────────────────

class PrivacySetting(models.Model):
    """Per-user privacy and data sharing preferences."""

    class ProfileVisibility(models.TextChoices):
        PUBLIC = "public", "Public"
        REGISTERED = "registered", "Registered Users Only"
        EMPLOYERS = "employers", "Verified Employers Only"
        PRIVATE = "private", "Private"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="privacy_settings"
    )
    profile_visibility = models.CharField(
        max_length=20, choices=ProfileVisibility.choices,
        default=ProfileVisibility.REGISTERED
    )
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)
    show_salary_expectation = models.BooleanField(default=False)
    allow_recruiter_messages = models.BooleanField(default=True)
    allow_agency_access = models.BooleanField(default=True)
    show_in_search = models.BooleanField(default=True)
    allow_ai_matching = models.BooleanField(default=True)
    allow_data_enrichment = models.BooleanField(default=False)
    email_notification_frequency = models.CharField(
        max_length=20, default="daily",
        choices=[("realtime", "Real-time"), ("daily", "Daily"), ("weekly", "Weekly"), ("off", "Off")]
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cx_privacy_setting"

    def __str__(self):
        return f"Privacy: {self.user} ({self.get_profile_visibility_display()})"
