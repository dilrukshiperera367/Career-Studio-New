"""
Agency Compliance models.
Document collection, work authorization, license/certification tracking,
credential expiry, background checks, client-specific compliance packs,
consent logs, audit vault, suppression lists.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class CompliancePack(models.Model):
    """
    A named set of compliance requirements (e.g., 'Healthcare Pack', 'Trades Pack').
    Can be associated with a client or used as a default.
    """

    class PackType(models.TextChoices):
        GENERAL = "general", "General"
        HEALTHCARE = "healthcare", "Healthcare"
        TRADES = "trades", "Skilled Trades"
        IT = "it", "IT / Technology"
        FINANCE = "finance", "Finance / Banking"
        EDUCATION = "education", "Education"
        EXECUTIVE = "executive", "Executive Search"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="compliance_packs"
    )
    name = models.CharField(max_length=200)
    pack_type = models.CharField(max_length=20, choices=PackType.choices, default=PackType.GENERAL)
    description = models.TextField(blank=True)
    required_document_types = models.JSONField(default=list)
    required_checks = models.JSONField(default=list)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="compliance_packs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compl_pack"

    def __str__(self):
        return f"{self.name} ({self.get_pack_type_display()})"


class ComplianceChecklist(models.Model):
    """
    Compliance checklist instance for a specific candidate / assignment.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed / Non-Compliant"
        WAIVED = "waived", "Waived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="compliance_checklists"
    )
    pack = models.ForeignKey(
        CompliancePack,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="checklists",
    )
    candidate = models.ForeignKey(
        "submissions.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="compliance_checklists",
    )
    assignment = models.ForeignKey(
        "contractor_ops.Assignment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="compliance_checklists",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_checklists"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compl_checklist"

    def __str__(self):
        return f"Compliance: {self.candidate} [{self.get_status_display()}]"


class BackgroundCheck(models.Model):
    """Background check record for a candidate."""

    class CheckType(models.TextChoices):
        CRIMINAL = "criminal", "Criminal History"
        CREDIT = "credit", "Credit Check"
        EMPLOYMENT = "employment", "Employment Verification"
        EDUCATION = "education", "Education Verification"
        REFERENCE = "reference", "Reference Check"
        DRUG_SCREEN = "drug_screen", "Drug Screen"
        GLOBAL_WATCH = "global_watch", "Global Watchlist"
        RIGHT_TO_WORK = "right_to_work", "Right to Work"

    class Result(models.TextChoices):
        PENDING = "pending", "Pending"
        CLEAR = "clear", "Clear"
        CONSIDER = "consider", "Consider (Review Required)"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="background_checks"
    )
    candidate = models.ForeignKey(
        "submissions.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="background_checks",
    )
    check_type = models.CharField(max_length=30, choices=CheckType.choices)
    provider = models.CharField(max_length=100, blank=True)
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.PENDING)
    ordered_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    report_url = models.URLField(blank=True)
    initiated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="ordered_checks"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "compl_background_check"
        ordering = ["-ordered_at"]

    def __str__(self):
        return f"{self.get_check_type_display()} – {self.candidate}: {self.get_result_display()}"


class Credential(models.Model):
    """License, certification, or credential held by a candidate."""

    class CredentialType(models.TextChoices):
        LICENSE = "license", "Professional License"
        CERTIFICATION = "certification", "Certification"
        DEGREE = "degree", "Academic Degree"
        SAFETY_CERT = "safety_cert", "Safety Certificate"
        INSURANCE = "insurance", "Insurance / Indemnity"
        MEMBERSHIP = "membership", "Professional Membership"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRING_SOON = "expiring_soon", "Expiring Soon"
        EXPIRED = "expired", "Expired"
        PENDING_RENEWAL = "pending_renewal", "Pending Renewal"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(
        "submissions.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    credential_type = models.CharField(max_length=30, choices=CredentialType.choices)
    title = models.CharField(max_length=200)
    issuing_body = models.CharField(max_length=200, blank=True)
    credential_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ACTIVE)
    document_url = models.URLField(blank=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_creds"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compl_credential"
        ordering = ["expiry_date"]

    def __str__(self):
        return f"{self.title} ({self.get_credential_type_display()}) – {self.candidate}"


class ConsentLog(models.Model):
    """Candidate consent log for data processing, outreach, and submission."""

    class ConsentType(models.TextChoices):
        DATA_PROCESSING = "data_processing", "Data Processing Consent"
        MARKETING = "marketing", "Marketing / Outreach"
        RIGHT_TO_REPRESENT = "right_to_represent", "Right to Represent"
        BACKGROUND_CHECK = "background_check", "Background Check Consent"
        TERMS = "terms", "Terms & Conditions"
        PRIVACY_POLICY = "privacy_policy", "Privacy Policy"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="consent_logs"
    )
    candidate = models.ForeignKey(
        "submissions.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="consent_logs",
    )
    consent_type = models.CharField(max_length=30, choices=ConsentType.choices)
    granted = models.BooleanField(default=True)
    granted_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    method = models.CharField(
        max_length=30,
        choices=[("email", "Email"), ("portal", "Portal"), ("verbal", "Verbal"), ("form", "Form")],
        default="portal",
    )
    document_version = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "compl_consent_log"
        ordering = ["-granted_at"]

    def __str__(self):
        return f"{self.get_consent_type_display()} – {self.candidate}"
