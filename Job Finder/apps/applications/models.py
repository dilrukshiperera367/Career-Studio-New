"""Applications app — Job application tracking.
11 status states, ATS link, match scoring.
"""
import uuid
from django.db import models
from django.conf import settings


class Application(models.Model):
    """A seeker's application to a particular job listing."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        VIEWED = "viewed", "Viewed"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        ASSESSMENT = "assessment", "Assessment"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        ON_HOLD = "on_hold", "On Hold"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("jobs.JobListing", on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="applications")

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED)
    resume = models.ForeignKey("candidates.SeekerResume", on_delete=models.SET_NULL, null=True, blank=True)
    cover_letter = models.TextField(blank=True, default="")
    screening_answers = models.JSONField(default=dict, blank=True)

    # Match scoring
    match_score = models.FloatField(null=True, blank=True)
    match_breakdown = models.JSONField(default=dict, blank=True)

    # Employer notes (private)
    employer_notes = models.TextField(blank=True, default="")
    employer_rating = models.IntegerField(null=True, blank=True)

    # ATS link
    ats_application_id = models.CharField(max_length=100, blank=True, default="")
    ats_stage = models.CharField(max_length=100, blank=True, default="")
    ats_synced_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    shortlisted_at = models.DateTimeField(null=True, blank=True)
    interviewed_at = models.DateTimeField(null=True, blank=True)
    offered_at = models.DateTimeField(null=True, blank=True)
    hired_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    # ── Marketplace Enhancements ──
    apply_method_used = models.CharField(
        max_length=15,
        choices=[
            ("quick_apply", "Quick Apply"), ("full_profile", "Full Profile"),
            ("resume_upload", "Resume Upload"), ("external", "External"),
        ],
        blank=True, default="full_profile",
        help_text="Which apply flow the seeker used",
    )
    autofill_used = models.BooleanField(default=False, help_text="Was autofill used to populate the application?")
    is_draft = models.BooleanField(default=False, help_text="Saved-draft not yet submitted")
    completion_percentage = models.IntegerField(default=100, help_text="Application completeness (0-100%)")
    external_apply_tracked = models.BooleanField(default=False,
                                                   help_text="Tracked external redirect to employer site")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_applications"
        unique_together = ["job", "applicant"]
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["applicant", "status"], name="idx_app_applicant_status"),
            models.Index(fields=["employer", "status"], name="idx_app_employer_status"),
            models.Index(fields=["job", "status"], name="idx_app_job_status"),
        ]

    def __str__(self):
        return f"Application {self.id} — {self.applicant} → {self.job}"


class ApplicationStatusHistory(models.Model):
    """Audit trail for application status changes."""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=12, blank=True, default="")
    new_status = models.CharField(max_length=12)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_application_status_history"
        ordering = ["-changed_at"]


class ApplicationNote(models.Model):
    """Private seeker notes on an application. #283"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="seeker_notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_application_notes"
        ordering = ["-created_at"]


class InterviewSchedule(models.Model):
    """Interview slot for an application. #291"""

    class InterviewType(models.TextChoices):
        PHONE = "phone", "Phone Interview"
        VIDEO = "video", "Video Interview"
        IN_PERSON = "in_person", "In-Person Interview"
        TECHNICAL = "technical", "Technical Interview"
        PANEL = "panel", "Panel Interview"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    interview_type = models.CharField(max_length=15, choices=InterviewType.choices, default=InterviewType.VIDEO)
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    location = models.CharField(max_length=500, blank=True, default="")  # address or meeting link
    notes = models.TextField(blank=True, default="")
    is_confirmed = models.BooleanField(default=False)  # seeker confirmed attendance
    outcome = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("passed", "Passed"), ("failed", "Failed"), ("no_show", "No Show"), ("rescheduled", "Rescheduled")],
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_interview_schedules"
        ordering = ["-scheduled_at"]


class JobOffer(models.Model):
    """Job offer details for a hired application. #292"""

    class OfferStatus(models.TextChoices):
        PENDING = "pending", "Pending Response"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        NEGOTIATING = "negotiating", "Under Negotiation"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="offer")
    offered_salary = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    offer_letter_url = models.URLField(max_length=500, blank=True, default="")
    additional_benefits = models.JSONField(default=list, blank=True)
    offer_status = models.CharField(max_length=12, choices=OfferStatus.choices, default=OfferStatus.PENDING)
    declined_reason = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_job_offers"


# ── Feature 5 additions ───────────────────────────────────────────────────────

class WithdrawalReason(models.Model):
    """Reason a seeker withdrew an application. Powers analytics on drop-off."""
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="withdrawal_reason")
    reason_code = models.CharField(max_length=30, choices=[
        ("accepted_other_offer", "Accepted Another Offer"),
        ("salary_mismatch", "Salary Not Matching"),
        ("role_not_right", "Role Not Right Fit"),
        ("no_response", "Employer Not Responding"),
        ("location_issue", "Location / Commute Issue"),
        ("company_concerns", "Concerns About Company"),
        ("still_exploring", "Still Exploring Options"),
        ("other", "Other"),
    ])
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_withdrawal_reasons"


class ApplicationTask(models.Model):
    """Post-apply task checklist item for the seeker (prepare portfolio, research company, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    is_done = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_application_tasks"
        ordering = ["sort_order", "due_date"]

    def __str__(self):
        return f"Task: {self.title} for {self.application_id}"


class FollowUpNudge(models.Model):
    """Scheduled follow-up nudge for an application."""
    class NudgeType(models.TextChoices):
        INCOMPLETE_DRAFT = "incomplete_draft", "Finish Incomplete Application"
        NO_RESPONSE = "no_response", "Follow Up — No Response"
        INTERVIEW_PREP = "interview_prep", "Interview Preparation Reminder"
        OFFER_EXPIRING = "offer_expiring", "Offer Expiring Soon"
        WEEKLY_UPDATE = "weekly_update", "Weekly Application Update"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="nudges")
    nudge_type = models.CharField(max_length=20, choices=NudgeType.choices)
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    is_dismissed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_follow_up_nudges"
        ordering = ["scheduled_for"]

    def __str__(self):
        return f"Nudge({self.nudge_type}) → {self.application_id} @ {self.scheduled_for:%Y-%m-%d}"


class ExternalApplicationTracker(models.Model):
    """Tracks applications submitted directly on an employer's external site."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="external_applications")
    company_name = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200)
    job_url = models.URLField(max_length=500, blank=True, default="")
    employer_link = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=15, choices=[
        ("applied", "Applied"), ("interviewing", "Interviewing"),
        ("offer", "Offer Received"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"),
    ], default="applied")
    applied_date = models.DateField()
    notes = models.TextField(blank=True, default="")
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_external_application_tracker"
        ordering = ["-applied_date"]

    def __str__(self):
        return f"External: {self.user} → {self.job_title} @ {self.company_name}"


class BatchApplySession(models.Model):
    """Records a multi-job batch apply flow."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="batch_apply_sessions")
    job_ids = models.JSONField(default=list, help_text="List of JobListing UUIDs in this batch")
    applied_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    cover_letter_used = models.TextField(blank=True, default="")
    resume_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jf_batch_apply_sessions"
        ordering = ["-created_at"]

