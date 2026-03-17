"""
Agency Trust & Safety models.
Recruiter identity verification, agency/client verification, suspicious job detection,
scam outreach detection, candidate abuse reports, moderation queue,
trust scores, impersonation detection, KYC for agencies.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class AgencyTrustProfile(models.Model):
    """
    Trust and verification status for an agency on the platform.
    """

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        PENDING = "pending", "Pending Verification"
        VERIFIED = "verified", "Verified"
        SUSPENDED = "suspended", "Suspended"
        BLACKLISTED = "blacklisted", "Blacklisted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.OneToOneField(
        "agencies.Agency", on_delete=models.CASCADE, related_name="trust_profile"
    )
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED
    )
    domain_verified = models.BooleanField(default=False)
    domain = models.CharField(max_length=200, blank=True)
    business_reg_verified = models.BooleanField(default=False)
    business_reg_number = models.CharField(max_length=100, blank=True)
    tax_id_verified = models.BooleanField(default=False)
    # KYC
    kyc_completed = models.BooleanField(default=False)
    kyc_completed_at = models.DateTimeField(null=True, blank=True)
    kyc_provider = models.CharField(max_length=100, blank=True)
    # Insurance
    professional_insurance_verified = models.BooleanField(default=False)
    insurance_expiry = models.DateField(null=True, blank=True)
    # Trust score (0-100)
    trust_score = models.IntegerField(default=50)
    trust_score_updated_at = models.DateTimeField(null=True, blank=True)
    # Payout risk
    payout_risk_level = models.CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
        default="medium",
    )
    # Flags
    impersonation_flag = models.BooleanField(default=False)
    fraud_flag = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)
    flagged_at = models.DateTimeField(null=True, blank=True)
    flagged_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="trust_flags"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trust_agency_profile"

    def __str__(self):
        return f"Trust: {self.agency.name} [{self.get_verification_status_display()}]"


class AbuseReport(models.Model):
    """
    Abuse report filed by a candidate, client, or staff member.
    """

    class ReportType(models.TextChoices):
        SCAM_JOB = "scam_job", "Fraudulent Job Posting"
        IMPERSONATION = "impersonation", "Agency Impersonation"
        FAKE_CLIENT = "fake_client", "Fake Client"
        HARASSMENT = "harassment", "Recruiter Harassment"
        DATA_MISUSE = "data_misuse", "Candidate Data Misuse"
        PAYMENT_FRAUD = "payment_fraud", "Payment Fraud"
        SUSPICIOUS_OUTREACH = "suspicious_outreach", "Suspicious Outreach"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"
        ESCALATED = "escalated", "Escalated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    # What is being reported (flexible FK pattern)
    reported_agency = models.ForeignKey(
        "agencies.Agency",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="abuse_reports",
    )
    reported_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="abuse_reports_against"
    )
    reported_job_order_id = models.UUIDField(null=True, blank=True)
    # Reporter
    reporter = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="filed_abuse_reports"
    )
    reporter_email = models.EmailField(blank=True)  # for anonymous reports
    description = models.TextField()
    evidence_urls = models.JSONField(default=list)
    # Moderation
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderated_abuse_reports",
    )
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    reported_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trust_abuse_report"
        ordering = ["-reported_at"]

    def __str__(self):
        return f"Abuse Report [{self.get_report_type_display()}] – {self.get_status_display()}"


class SuspiciousActivityLog(models.Model):
    """
    System-generated log of suspicious signals: scam patterns, message/link scanning,
    unusual login patterns, mass outreach detection.
    """

    class SignalType(models.TextChoices):
        SCAM_LINK = "scam_link", "Scam / Phishing Link"
        MASS_OUTREACH = "mass_outreach", "Unusual Mass Outreach"
        IMPERSONATION = "impersonation", "Impersonation Signal"
        SUSPICIOUS_JOB = "suspicious_job", "Suspicious Job Content"
        PAYMENT_REQUEST = "payment_request", "Upfront Payment Request"
        RAPID_LOGIN = "rapid_login", "Rapid/Unusual Login"
        API_ABUSE = "api_abuse", "API Rate Abuse"
        OTHER = "other", "Other"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signal_type = models.CharField(max_length=30, choices=SignalType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.LOW)
    agency = models.ForeignKey(
        "agencies.Agency",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="suspicious_logs",
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="suspicious_logs"
    )
    description = models.TextField()
    metadata = models.JSONField(default=dict)
    is_reviewed = models.BooleanField(default=False)
    review_outcome = models.CharField(max_length=200, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_suspicious_logs",
    )
    detected_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trust_suspicious_activity"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.get_signal_type_display()}"


class AuditLog(models.Model):
    """
    Immutable audit log for sensitive actions: field-level changes,
    submission sends, data exports, user deletions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    performed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_actions"
    )
    action = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    performed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "trust_audit_log"
        ordering = ["-performed_at"]

    def __str__(self):
        return f"Audit: {self.action} by {self.performed_by} at {self.performed_at}"
