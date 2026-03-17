"""Applications app — Applications, stage history, evaluations, interviews, offers, employees."""

import uuid
from django.db import models


class Application(models.Model):
    """A candidate's application to a specific job. The state machine object."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("rejected", "Rejected"),
        ("hired", "Hired"),
        ("withdrawn", "Withdrawn"),
        ("on_hold", "On Hold"),
    ]

    REJECTION_REASON_CHOICES = [
        ("unqualified", "Unqualified"),
        ("salary_mismatch", "Salary Mismatch"),
        ("no_show", "No Show"),
        ("culture_fit", "Culture Fit"),
        ("position_filled", "Position Filled"),
        ("overqualified", "Overqualified"),
        ("insufficient_experience", "Insufficient Experience"),
        ("failed_assessment", "Failed Assessment"),
        ("candidate_withdrew", "Candidate Withdrew"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="applications")
    resume = models.ForeignKey(
        "candidates.ResumeDocument", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="applications"
    )
    current_stage = models.ForeignKey(
        "jobs.PipelineStage", on_delete=models.PROTECT, related_name="current_applications"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    source = models.CharField(max_length=100, blank=True, default="direct")
    screening_answers = models.JSONField(default=dict, blank=True)
    score = models.FloatField(null=True, blank=True, help_text="Computed ranking score")
    score_breakdown = models.JSONField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default="")

    # Enhanced fields (Features 141-150)
    rejection_reason = models.CharField(
        max_length=50, choices=REJECTION_REASON_CHOICES, blank=True, default=""
    )
    rejection_notes = models.TextField(blank=True, default="")
    is_priority = models.BooleanField(default=False, help_text="Starred/pinned application")
    on_hold = models.BooleanField(default=False)
    hold_reason = models.TextField(blank=True, default="")
    stage_checklist_completed = models.JSONField(
        default=dict, blank=True,
        help_text='{"stage_id": ["item1_done", "item2_done"]}'
    )
    assigned_recruiter = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_applications"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "applications"
        unique_together = [("job", "candidate")]
        indexes = [
            models.Index(fields=["tenant", "job", "status"]),
            models.Index(fields=["tenant", "candidate"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "is_priority"]),
        ]

    def __str__(self):
        return f"{self.candidate.full_name} → {self.job.title}"


class StageHistory(models.Model):
    """Immutable audit trail of application stage changes. NEVER update or delete."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="stage_history")
    from_stage = models.ForeignKey(
        "jobs.PipelineStage", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transitions_from"
    )
    to_stage = models.ForeignKey(
        "jobs.PipelineStage", on_delete=models.CASCADE, related_name="transitions_to"
    )
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stage_changes"
    )
    event_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    notes = models.TextField(blank=True, default="")
    duration_hours = models.FloatField(null=True, blank=True, help_text="Hours spent in previous stage")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stage_history"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["tenant", "application", "created_at"]),
            models.Index(fields=["tenant", "created_at"]),
        ]

    def __str__(self):
        from_name = self.from_stage.name if self.from_stage else "—"
        return f"{from_name} → {self.to_stage.name}"

    def save(self, *args, **kwargs):
        if self.pk and StageHistory.objects.filter(pk=self.pk).exists():
            raise ValueError("StageHistory records are immutable. Cannot update.")
        super().save(*args, **kwargs)


class Evaluation(models.Model):
    """Feedback/scorecard submitted by an interviewer or reviewer."""

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    RECOMMENDATION_CHOICES = [
        ("strong_yes", "Strong Yes"),
        ("yes", "Yes"),
        ("neutral", "Neutral"),
        ("no", "No"),
        ("strong_no", "Strong No"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="evaluations")
    stage = models.ForeignKey("jobs.PipelineStage", on_delete=models.CASCADE)
    evaluator = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="evaluations")
    overall_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES, default="neutral")
    criteria_scores = models.JSONField(
        default=dict, blank=True,
        help_text='{"technical": 4, "communication": 5, "culture_fit": 3}'
    )
    strengths = models.TextField(blank=True, default="")
    concerns = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluations"
        unique_together = [("application", "stage", "evaluator")]

    def __str__(self):
        return f"Eval by {self.evaluator.email} — {self.recommendation}"


class Interview(models.Model):
    """A scheduled interview for an application."""

    TYPE_CHOICES = [
        ("video", "Video"),
        ("phone", "Phone"),
        ("onsite", "On-site"),
        ("take_home", "Take Home"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
        ("rescheduled", "Rescheduled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="interviews")
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="interviews",
        null=True, blank=True,
    )
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="interviews")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="interviews")
    interview_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="video")
    date = models.DateField()
    time = models.TimeField()
    duration = models.IntegerField(default=45, help_text="Duration in minutes")
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="conducted_interviews",
    )
    interviewer_name = models.CharField(max_length=200, blank=True, default="")
    location = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    notes = models.TextField(blank=True, default="")
    feedback = models.TextField(blank=True, default="")
    rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating")

    # Enhanced fields (Features 57-68)
    round_number = models.IntegerField(default=1, help_text="Interview round (1, 2, 3...)")
    round_name = models.CharField(max_length=100, blank=True, default="",
        help_text="Phone Screen, Technical, Culture Fit")
    no_show_by = models.CharField(max_length=20, blank=True, default="",
        help_text="candidate or interviewer")
    reschedule_count = models.IntegerField(default=0)
    feedback_deadline = models.DateTimeField(null=True, blank=True)
    decision = models.CharField(max_length=20, blank=True, default="",
        help_text="advance, reject, hold — set by hiring manager after feedback")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interviews"
        ordering = ["-date", "-time"]
        indexes = [
            models.Index(fields=["tenant", "date"]),
            models.Index(fields=["tenant", "candidate"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "interviewer"]),
        ]

    def __str__(self):
        return f"Interview: {self.candidate.full_name} — {self.job.title} ({self.date})"


class InterviewPanel(models.Model):
    """Multiple interviewers per interview — each submits separate feedback."""

    STATUS_CHOICES = [
        ("pending", "Pending Feedback"),
        ("submitted", "Feedback Submitted"),
        ("declined", "Declined"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name="panel_members")
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="interview_panels"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    feedback = models.TextField(blank=True, default="")
    rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interview_panels"
        unique_together = [("interview", "interviewer")]

    def __str__(self):
        return f"Panel: {self.interviewer.email} for {self.interview}"


class InterviewScorecard(models.Model):
    """Structured evaluation criteria for an interview panel member."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    panel = models.ForeignKey(InterviewPanel, on_delete=models.CASCADE, related_name="scorecards")
    criteria_name = models.CharField(max_length=100,
        help_text="Communication, Technical Skills, Problem Solving, Culture Fit")
    rating = models.IntegerField(help_text="1-5 rating")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "interview_scorecards"
        unique_together = [("panel", "criteria_name")]

    def __str__(self):
        return f"{self.criteria_name}: {self.rating}/5"


class Offer(models.Model):
    """A job offer extended to a candidate."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
        ("withdrawn", "Withdrawn"),
    ]

    APPROVAL_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    DECLINE_REASON_CHOICES = [
        ("better_offer", "Better Offer Elsewhere"),
        ("salary_too_low", "Salary Too Low"),
        ("relocation", "Relocation Issues"),
        ("counter_offer", "Counter-offer from Current Employer"),
        ("personal", "Personal Reasons"),
        ("role_mismatch", "Role Not as Expected"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offers")
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="offers",
        null=True, blank=True,
    )
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="offers")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="offers")
    salary = models.CharField(max_length=100, blank=True, default="")
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="USD")
    start_date = models.DateField(null=True, blank=True)
    benefits = models.TextField(blank=True, default="")
    equity = models.CharField(max_length=200, blank=True, default="")
    signing_bonus = models.CharField(max_length=100, blank=True, default="")
    bonus = models.CharField(max_length=100, blank=True, default="")
    total_compensation = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default="pending")
    approver = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_offers",
    )
    notes = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)

    # Enhanced fields (Features 151-160)
    negotiation_history = models.JSONField(default=list, blank=True,
        help_text='[{"round": 1, "offered": 150000, "counter": 165000, "date": "..."}]')
    decline_reason = models.CharField(
        max_length=50, choices=DECLINE_REASON_CHOICES, blank=True, default=""
    )
    decline_notes = models.TextField(blank=True, default="")
    verbal_accepted = models.BooleanField(default=False)
    background_check_status = models.CharField(
        max_length=20, blank=True, default="",
        help_text="pending, in_progress, cleared, failed"
    )
    approval_chain = models.JSONField(default=list, blank=True,
        help_text='[{"level": "manager", "user_id": "...", "status": "approved"}]')

    # HRM back-write fields populated after employee record is created in HRM
    hrm_employee_id = models.UUIDField(
        null=True, blank=True,
        help_text="UUID of the HRM Employee record created from this offer"
    )
    hrm_employee_number = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Human-readable employee number assigned by HRM (e.g., EMP-001)"
    )
    # E-signature tracking
    esign_provider = models.CharField(max_length=50, blank=True, default="",
        help_text="docusign, hellosign, adobe_sign, internal")
    esign_envelope_id = models.CharField(max_length=255, blank=True, default="")
    esign_signed_at = models.DateTimeField(null=True, blank=True)
    esign_document_url = models.CharField(max_length=500, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "offers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "candidate"]),
        ]

    def __str__(self):
        return f"Offer: {self.candidate.full_name} — {self.job.title} ({self.status})"


class Employee(models.Model):
    """A hired candidate — bridges ATS to HR. Auto-created when application → hired."""

    STATUS_CHOICES = [
        ("onboarding", "Onboarding"),
        ("probation", "Probation"),
        ("active", "Active"),
        ("terminated", "Terminated"),
        ("resigned", "Resigned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="employees")
    candidate = models.OneToOneField(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="employee_record"
    )
    application = models.OneToOneField(
        Application, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employee_record"
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, related_name="employees")
    employee_id = models.CharField(max_length=50, blank=True, default="", help_text="Internal employee ID")
    department = models.CharField(max_length=150, blank=True, default="")
    title = models.CharField(max_length=255, blank=True, default="")
    manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="direct_reports"
    )
    buddy = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mentees"
    )
    hire_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="onboarding")

    # Post-hire tracking (Features 171-180)
    goals_30 = models.JSONField(default=list, blank=True)
    goals_60 = models.JSONField(default=list, blank=True)
    goals_90 = models.JSONField(default=list, blank=True)
    satisfaction_score = models.IntegerField(null=True, blank=True, help_text="1-5 from 30-day survey")
    hiring_quality_score = models.IntegerField(null=True, blank=True,
        help_text="1-5 rated 6 months after hire")

    # Termination
    termination_date = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True, default="")
    exit_interview_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employees"
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "department"]),
        ]

    def __str__(self):
        return f"Employee: {self.candidate.full_name} ({self.status})"


class OnboardingTask(models.Model):
    """Task in a new hire's onboarding checklist."""

    CATEGORY_CHOICES = [
        ("it", "IT Setup"),
        ("hr", "HR/Admin"),
        ("training", "Training"),
        ("equipment", "Equipment"),
        ("intro", "Introductions"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="onboarding_tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    due_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="onboarding_assignments"
    )
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_tasks"
        ordering = ["due_date"]

    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"[{status}] {self.title}"


class DebriefSession(models.Model):
    """
    Post-interview debrief session: hiring team discusses an application
    collaboratively before making an advance/reject decision.
    """

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="debrief_sessions")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="debrief_sessions")
    facilitator = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="facilitated_debriefs",
    )
    participants = models.ManyToManyField(
        "accounts.User", blank=True, related_name="debrief_participants",
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    decision = models.CharField(
        max_length=20,
        choices=[("advance", "Advance"), ("reject", "Reject"), ("hold", "Hold"), ("pending", "Pending")],
        default="pending",
    )
    summary = models.TextField(blank=True, default="")
    action_items = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "debrief_sessions"
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["tenant", "application"]),
        ]

    def __str__(self):
        return f"Debrief: {self.application_id} ({self.status})"


class CalibrationSession(models.Model):
    """
    Calibration session to align interviewer scoring standards across a job.
    Records which criteria were discussed and agreed weight adjustments.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="calibration_sessions")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="calibration_sessions")
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="owned_calibrations",
    )
    participants = models.ManyToManyField(
        "accounts.User", blank=True, related_name="calibration_participants",
    )
    session_date = models.DateField(null=True, blank=True)
    criteria_discussed = models.JSONField(
        default=list, blank=True,
        help_text='[{"criterion": "Technical", "agreed_weight": 0.4, "notes": "..."}]',
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calibration_sessions"
        ordering = ["-session_date"]

    def __str__(self):
        return f"Calibration: {self.job_id} on {self.session_date}"


class ApplicationAppeal(models.Model):
    """
    A candidate or recruiter can raise an appeal if they believe a rejection
    was erroneous. Supports structured review and override capture for EU AI Act.
    """

    STATUS_CHOICES = [
        ("open", "Open"),
        ("under_review", "Under Review"),
        ("upheld", "Upheld — Decision Reversed"),
        ("dismissed", "Dismissed — Original Decision Stands"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="application_appeals")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="appeals")
    raised_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="raised_appeals",
    )
    reason = models.TextField()
    supporting_evidence = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_appeals",
    )
    reviewer_notes = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    # EU AI Act: capture human override details
    ai_decision_overridden = models.BooleanField(default=False)
    override_justification = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "application_appeals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "application"]),
        ]

    def __str__(self):
        return f"Appeal: {self.application_id} ({self.status})"


class HiringManagerNote(models.Model):
    """
    Private note from the hiring manager on an application.
    Separate from recruiter notes to support independent evaluation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_notes")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="hm_notes")
    author = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hm_application_notes",
    )
    content = models.TextField()
    is_visible_to_recruiter = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hiring_manager_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"HM Note on {self.application_id}"
