"""Trust Ops — strike records, suspensions, scam alerts, phishing reports, identity proofing."""
import uuid
from django.db import models
from django.conf import settings


class StrikeRecord(models.Model):
    """Strike issued to an employer or recruiter for policy violations."""
    class StrikeReason(models.TextChoices):
        FAKE_JOB = "fake_job", "Fake Job Posting"
        SCAM_BEHAVIOR = "scam", "Scam Behavior"
        HARASSMENT = "harassment", "User Harassment"
        PAYMENT_REQUEST = "payment_request", "Illegal Payment Request"
        MISLEADING_INFO = "misleading", "Misleading Job Info"
        DUPLICATE_POSTING = "duplicate", "Excessive Duplicate Postings"
        POLICY_VIOLATION = "policy", "General Policy Violation"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="strikes_received")
    target_employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="strikes")
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name="strikes_issued")
    reason = models.CharField(max_length=20, choices=StrikeReason.choices)
    description = models.TextField(blank=True, default="")
    related_job_id = models.UUIDField(null=True, blank=True)
    related_report_id = models.UUIDField(null=True, blank=True)
    strike_number = models.IntegerField(default=1, help_text="1st, 2nd, 3rd strike")
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_strike_records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Strike #{self.strike_number}: {self.target_user} — {self.reason}"


class SuspensionRecord(models.Model):
    """Active or historical suspension of an employer/user account."""
    class SuspensionType(models.TextChoices):
        TEMPORARY = "temporary", "Temporary"
        PERMANENT = "permanent", "Permanent"
        UNDER_REVIEW = "under_review", "Under Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="suspensions")
    target_employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="suspensions")
    suspension_type = models.CharField(max_length=15, choices=SuspensionType.choices,
                                       default=SuspensionType.TEMPORARY)
    reason = models.TextField()
    suspended_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                     related_name="suspensions_issued")
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  blank=True, related_name="suspensions_lifted")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_suspension_records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Suspension: {self.target_user} ({self.suspension_type})"


class ScamAlert(models.Model):
    """Public or internal scam alert attached to a job or employer."""
    class AlertLevel(models.TextChoices):
        WARNING = "warning", "Warning"
        HIGH_RISK = "high_risk", "High Risk"
        CONFIRMED_SCAM = "confirmed_scam", "Confirmed Scam"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("jobs.JobListing", on_delete=models.SET_NULL, null=True, blank=True,
                            related_name="scam_alerts")
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="scam_alerts")
    alert_level = models.CharField(max_length=15, choices=AlertLevel.choices, default=AlertLevel.WARNING)
    alert_message = models.TextField()
    is_public = models.BooleanField(default=False, help_text="Show warning to seekers")
    is_resolved = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jf_scam_alerts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScamAlert [{self.alert_level}]: {self.alert_message[:60]}"


class PhishingMessageReport(models.Model):
    """Phishing message reported by a seeker."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWED = "reviewed", "Reviewed"
        ACTIONED = "actioned", "Action Taken"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="phishing_reports")
    message_thread_id = models.UUIDField(null=True, blank=True)
    sender_email = models.EmailField(blank=True, default="")
    suspicious_url = models.URLField(max_length=500, blank=True, default="")
    description = models.TextField()
    screenshot_url = models.URLField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="phishing_reviews")
    resolution_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jf_phishing_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PhishingReport: {self.reporter} ({self.status})"


class IdentityProofRequest(models.Model):
    """Identity verification request for high-risk poster."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Documents Submitted"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="identity_proofs")
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL, null=True, blank=True)
    trigger_reason = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    documents_submitted = models.JSONField(default=list)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name="identity_verifications")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jf_identity_proof_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"IDProof: {self.user} ({self.status})"
