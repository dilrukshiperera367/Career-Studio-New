"""Trust Ops app — Platform integrity, job moderation, fraud detection, and safe sharing."""

import uuid
from django.db import models


class RecruiterVerification(models.Model):
    """Verification status for a recruiter user account."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
        ("revoked", "Revoked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="recruiter_verifications")
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="recruiter_verification")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verification_method = models.CharField(
        max_length=50, blank=True, default="",
        help_text="e.g. linkedin_oauth, manual_id_check, company_email"
    )
    verified_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verifications_performed"
    )
    verification_notes = models.TextField(blank=True, default="")
    identity_document_url = models.URLField(blank=True, default="", help_text="Stored securely; access-logged")
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruiter_verifications"

    def __str__(self):
        return f"{self.user_id} — {self.status}"


class EmployerDomainVerification(models.Model):
    """DNS/email-based verification that a tenant actually owns their claimed employer domain."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="domain_verifications")
    domain = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    dns_token = models.CharField(max_length=128, blank=True, default="", help_text="TXT record value to add to DNS")
    last_checked_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "employer_domain_verifications"
        unique_together = [("tenant", "domain")]

    def __str__(self):
        return f"{self.domain} — {self.status}"


class JobModerationQueue(models.Model):
    """A job posting flagged for human moderation review."""

    REASON_CHOICES = [
        ("discriminatory_language", "Discriminatory Language"),
        ("misleading_content", "Misleading Content"),
        ("spam", "Spam / Duplicate"),
        ("illegal_requirement", "Illegal Requirement"),
        ("ai_flagged", "AI-flagged for Review"),
        ("user_report", "User Report"),
        ("other", "Other"),
    ]

    DECISION_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("edited_approved", "Edited & Approved"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_moderation_queue")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="moderation_records")
    reason = models.CharField(max_length=40, choices=REASON_CHOICES)
    details = models.TextField(blank=True, default="")
    ai_confidence = models.FloatField(
        null=True, blank=True, help_text="AI-assigned confidence score 0–1 (EU AI Act — shown to reviewer)"
    )
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="moderated_jobs"
    )
    review_notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_moderation_queue"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "decision"]),
        ]

    def __str__(self):
        return f"Moderation: {self.job.title} ({self.reason})"


class SuspiciousSubmission(models.Model):
    """A candidate application or submission flagged for fraud signals."""

    SIGNAL_CHOICES = [
        ("duplicate_email", "Duplicate Email"),
        ("rapid_fire_applications", "Rapid-fire Applications"),
        ("vpn_proxy_detected", "VPN/Proxy Detected"),
        ("bot_behaviour", "Bot Behaviour"),
        ("stolen_resume", "Possible Stolen Resume"),
        ("contact_spoofing", "Contact Spoofing"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("flagged", "Flagged"),
        ("investigating", "Investigating"),
        ("confirmed_fraud", "Confirmed Fraud"),
        ("cleared", "Cleared"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="suspicious_submissions")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fraud_flags"
    )
    signals = models.JSONField(default=list, blank=True, help_text="List of triggered signal codes")
    risk_score = models.FloatField(default=0.0, help_text="0–100 composite fraud risk score")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="flagged")
    investigated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fraud_investigations"
    )
    resolution_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suspicious_submissions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Fraud flag (score={self.risk_score}) — {self.status}"


class AbuseReport(models.Model):
    """A report submitted by a candidate or user about platform abuse."""

    REPORT_TYPE_CHOICES = [
        ("fake_job", "Fake Job Posting"),
        ("harassment", "Recruiter Harassment"),
        ("data_misuse", "Data Misuse"),
        ("discriminatory_rejection", "Discriminatory Rejection"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_review", "In Review"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, null=True, blank=True,
        related_name="abuse_reports"
    )
    reporter_email = models.EmailField(blank=True, default="")
    report_type = models.CharField(max_length=40, choices=REPORT_TYPE_CHOICES)
    description = models.TextField()
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="abuse_reports"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_abuse_reports"
    )
    resolution = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "abuse_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Abuse report ({self.report_type}) — {self.status}"


class SafeShareLink(models.Model):
    """A time-limited, token-authenticated link for sharing candidate profiles externally."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="safe_share_links")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="safe_share_links"
    )
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="safe_share_links"
    )
    token = models.CharField(max_length=128, unique=True)
    shared_with_email = models.EmailField(blank=True, default="")
    pii_redacted = models.BooleanField(default=True, help_text="If True, name/contact info is hidden")
    fields_visible = models.JSONField(
        default=list, blank=True,
        help_text='["resume", "scores", "work_history"] — fields exposed via this link'
    )
    expires_at = models.DateTimeField()
    accessed_at = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="safe_share_links_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "safe_share_links"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SafeShare token for candidate {self.candidate_id}"


class DocumentScanResult(models.Model):
    """ClamAV / antivirus scan result for an uploaded document."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("clean", "Clean"),
        ("infected", "Infected"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="document_scan_results")
    file_url = models.URLField()
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    threat_name = models.CharField(max_length=255, blank=True, default="")
    scanned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_scan_results"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} — {self.status}"


class CandidateWatermark(models.Model):
    """A steganographic or visible watermark applied to a shared candidate document."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_watermarks")
    safe_share_link = models.ForeignKey(
        SafeShareLink, on_delete=models.CASCADE, related_name="watermarks"
    )
    original_file_url = models.URLField()
    watermarked_file_url = models.URLField()
    watermark_token = models.CharField(max_length=128, help_text="Embedded token for forensic tracing")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_watermarks"

    def __str__(self):
        return f"Watermark for share {self.safe_share_link_id}"
