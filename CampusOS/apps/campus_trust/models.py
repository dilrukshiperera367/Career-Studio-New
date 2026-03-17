"""CampusOS — Campus Trust & Safety models."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class EmployerVerification(TimestampedModel):
    """Verifies a CampusEmployer is a legitimate company."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.OneToOneField("campus_employers.CampusEmployer", on_delete=models.CASCADE, related_name="verification")

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("documents_requested", "Documents Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("suspended", "Suspended"),
    ]

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="pending")
    registration_number = models.CharField(max_length=100, blank=True)
    registration_document_url = models.URLField(blank=True)
    gstin = models.CharField(max_length=20, blank=True)
    verified_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="employer_verifications"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    trust_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employer.name} — {self.status}"


class AlumniVerification(TimestampedModel):
    """Verifies an alumni's graduation claims."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alumni = models.OneToOneField("alumni_mentors.AlumniProfile", on_delete=models.CASCADE, related_name="verification")

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")
    degree_certificate_url = models.URLField(blank=True)
    verified_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="alumni_verifications"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.alumni} — {self.status}"


class SuspiciousOpportunityFlag(TimestampedModel):
    """Flags a placement/internship opportunity as suspicious."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    FLAG_TYPE_CHOICES = [
        ("fake_company", "Fake Company"),
        ("upfront_fee", "Upfront Fee Required"),
        ("misleading_ctc", "Misleading CTC"),
        ("personal_data_abuse", "Personal Data Misuse"),
        ("discriminatory", "Discriminatory Criteria"),
        ("other", "Other"),
    ]

    CONTENT_TYPE_CHOICES = [
        ("internship", "Internship"),
        ("drive", "Placement Drive"),
        ("job_share", "Alumni Job Share"),
    ]

    flagged_by = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="opportunity_flags")
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    object_id = models.UUIDField(help_text="UUID of the flagged object")
    flag_type = models.CharField(max_length=25, choices=FLAG_TYPE_CHOICES)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[("open", "Open"), ("investigating", "Investigating"), ("resolved", "Resolved"), ("dismissed", "Dismissed")],
        default="open",
    )
    resolved_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_flags"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class AbuseReport(TimestampedModel):
    """Report abusive behaviour by a platform user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    REASON_CHOICES = [
        ("harassment", "Harassment"),
        ("spam", "Spam"),
        ("impersonation", "Impersonation"),
        ("inappropriate_content", "Inappropriate Content"),
        ("fraud", "Fraud / Scam"),
        ("other", "Other"),
    ]

    reported_by = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="abuse_reports_sent")
    reported_user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="abuse_reports_received")
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField()
    evidence_urls = models.JSONField(default=list)
    status = models.CharField(
        max_length=20,
        choices=[("open", "Open"), ("reviewing", "Reviewing"), ("actioned", "Actioned"), ("dismissed", "Dismissed")],
        default="open",
    )
    actioned_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="actioned_abuse_reports"
    )
    action_taken = models.TextField(blank=True)
    actioned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class TrustScore(TimestampedModel):
    """Aggregate computed trust score for any user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="trust_score")
    score = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    flags_count = models.PositiveIntegerField(default=0)
    abuse_reports_count = models.PositiveIntegerField(default=0)
    is_flagged = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)
    last_computed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {self.score}"
