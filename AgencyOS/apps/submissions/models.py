"""
Submissions app models.
Candidate submissions, shortlist packaging, ownership, right-to-represent,
submittal tracking, send-to-client audit, comparison, and revision requests.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class CandidateProfile(models.Model):
    """
    Agency-owned candidate master record.
    Source tracking, ownership windows, availability, work auth, history.
    """

    class OwnershipStatus(models.TextChoices):
        OWNED = "owned", "Owned"
        EXPIRED = "expired", "Ownership Expired"
        DISPUTED = "disputed", "Disputed"
        RELEASED = "released", "Released"

    class WorkAuthStatus(models.TextChoices):
        CITIZEN = "citizen", "Citizen"
        PR = "pr", "Permanent Resident"
        WORK_VISA = "work_visa", "Work Visa"
        NEEDS_SPONSORSHIP = "needs_sponsorship", "Needs Sponsorship"
        NOT_AUTHORIZED = "not_authorized", "Not Authorized"
        UNKNOWN = "unknown", "Unknown"

    class ContractPreference(models.TextChoices):
        CONTRACT_ONLY = "contract_only", "Contract Only"
        PERM_ONLY = "perm_only", "Permanent Only"
        BOTH = "both", "Both Contract & Perm"
        TEMP = "temp", "Temp / Ad-hoc"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="candidate_profiles"
    )
    # If linked to a platform user
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="agency_candidate_profiles"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    resume_url = models.URLField(blank=True)
    # Ownership
    owning_recruiter = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_candidates"
    )
    ownership_status = models.CharField(
        max_length=20, choices=OwnershipStatus.choices, default=OwnershipStatus.OWNED
    )
    ownership_expiry = models.DateTimeField(null=True, blank=True)
    # Availability
    available_from = models.DateField(null=True, blank=True)
    notice_period_days = models.IntegerField(null=True, blank=True)
    # Work auth
    work_auth_status = models.CharField(
        max_length=30, choices=WorkAuthStatus.choices, default=WorkAuthStatus.UNKNOWN
    )
    work_auth_country = models.CharField(max_length=100, blank=True)
    # Preferences
    contract_preference = models.CharField(
        max_length=20, choices=ContractPreference.choices, default=ContractPreference.BOTH
    )
    desired_salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    desired_salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    desired_rate_hourly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="USD")
    location_preferences = models.JSONField(default=list)
    willing_to_relocate = models.BooleanField(default=False)
    willing_to_travel = models.BooleanField(default=False)
    # Skills + quality
    skills = models.JSONField(default=list)
    quality_score = models.IntegerField(null=True, blank=True)
    # Flags
    do_not_submit = models.BooleanField(default=False)
    do_not_rehire = models.BooleanField(default=False)
    do_not_submit_reason = models.TextField(blank=True)
    # Contactability
    accepts_email = models.BooleanField(default=True)
    accepts_sms = models.BooleanField(default=False)
    accepts_whatsapp = models.BooleanField(default=False)
    # Source
    source = models.CharField(max_length=100, blank=True)
    source_detail = models.CharField(max_length=200, blank=True)
    # Redeployment
    is_redeployable = models.BooleanField(default=False)
    is_boomerang = models.BooleanField(default=False)
    is_silver_medalist = models.BooleanField(default=False)
    # Merge tracking
    merged_into = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="merged_from"
    )
    is_duplicate = models.BooleanField(default=False)
    # Summary
    recruiter_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sub_candidate_profile"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Submission(models.Model):
    """
    A candidate submission to a specific job order for a client.
    Includes ownership validation, packaging, audit trail.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted to Client"
        UNDER_REVIEW = "under_review", "Under Client Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW_REQUESTED = "interview_requested", "Interview Requested"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
        INTERVIEWED = "interviewed", "Interviewed"
        OFFER = "offer", "Offer Made"
        PLACED = "placed", "Placed"
        REJECTED = "rejected", "Rejected by Client"
        WITHDRAWN = "withdrawn", "Withdrawn by Candidate"
        ON_HOLD = "on_hold", "On Hold"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="submissions"
    )
    job_order = models.ForeignKey(
        "job_orders.JobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    # Legacy link
    legacy_submission = models.OneToOneField(
        "agencies.AgencySubmission",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="extended_submission",
    )
    candidate = models.ForeignKey(
        CandidateProfile, on_delete=models.CASCADE, related_name="submissions"
    )
    submitted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="submitted_submissions"
    )
    account_manager = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="am_submissions"
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    # Packaging
    recruiter_pitch = models.TextField(blank=True)
    tailored_resume_url = models.URLField(blank=True)
    cover_note = models.TextField(blank=True)
    match_score = models.IntegerField(null=True, blank=True)
    rank_in_shortlist = models.IntegerField(null=True, blank=True)
    # Ownership
    ownership_verified = models.BooleanField(default=False)
    right_to_represent_captured = models.BooleanField(default=False)
    right_to_represent_date = models.DateTimeField(null=True, blank=True)
    # Submittal limits & duplicate prevention
    duplicate_check_passed = models.BooleanField(default=True)
    # Client response
    client_notes = models.TextField(blank=True)
    client_reviewed_at = models.DateTimeField(null=True, blank=True)
    # Audit
    sent_to_client_at = models.DateTimeField(null=True, blank=True)
    sent_to_client_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_submissions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sub_submission"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.candidate} → {self.job_order} [{self.get_status_display()}]"


class SubmissionStatusHistory(models.Model):
    """Audit trail for submission status changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="status_history"
    )
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="submission_status_changes"
    )
    reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sub_status_history"
        ordering = ["-changed_at"]


class Shortlist(models.Model):
    """
    A formatted shortlist package sent to a client.
    Groups multiple submissions into a presentable deck.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent to Client"
        REVIEWED = "reviewed", "Client Reviewed"
        REVISION_REQUESTED = "revision_requested", "Revision Requested"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="shortlists"
    )
    job_order = models.ForeignKey(
        "job_orders.JobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shortlists",
    )
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    submissions = models.ManyToManyField(Submission, related_name="shortlists", blank=True)
    intro_message = models.TextField(blank=True)
    deck_url = models.URLField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_shortlists"
    )
    revision_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sub_shortlist"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Shortlist: {self.title} [{self.get_status_display()}]"


class SendToClientLog(models.Model):
    """Audit log when a submission or shortlist is sent to a client."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="send_logs"
    )
    submission = models.ForeignKey(
        Submission, null=True, blank=True, on_delete=models.CASCADE, related_name="send_logs"
    )
    shortlist = models.ForeignKey(
        Shortlist, null=True, blank=True, on_delete=models.CASCADE, related_name="send_logs"
    )
    sent_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="send_logs"
    )
    recipient_email = models.EmailField()
    method = models.CharField(
        max_length=30,
        choices=[("email", "Email"), ("portal", "Client Portal"), ("api", "API")],
        default="email",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "sub_send_to_client_log"
        ordering = ["-sent_at"]
