"""
MarketplaceOS — apps.delivery

Delivery Workspace — owns the session workflow after a booking is confirmed.

Models:
    Session              — Live session or async review delivery record
    SessionNote          — Shared notes within a session
    SessionDeliverable   — Files/documents delivered as part of a session
    SessionFeedbackForm  — Post-session feedback (rubric-based)
    SessionActionPlan    — Action plan built during/after a session
    SessionMilestone     — Trackable milestone attached to an action plan
    SessionAssignment    — Homework/assignment given by provider
    MockInterviewRubric  — Structured rubric for mock interview sessions
    AsyncReviewDelivery  — Async review workflow (document → markup → delivery)
"""
import uuid
from django.db import models
from django.conf import settings


class Session(models.Model):
    """
    Delivery record for a confirmed booking.
    One booking → one session.  Tracks the full session lifecycle:
    not_started → in_progress → ended → reviewed.
    """

    class SessionStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        ENDED = "ended", "Ended"
        REVIEWED = "reviewed", "Review Submitted"
        ASYNC_PENDING = "async_pending", "Async Review Pending"
        ASYNC_DELIVERED = "async_delivered", "Async Review Delivered"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="session",
    )
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.NOT_STARTED)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    actual_duration_minutes = models.IntegerField(null=True, blank=True)

    # Meeting metadata
    external_meeting_link = models.URLField(blank=True, default="")
    meeting_provider = models.CharField(max_length=50, blank=True, default="")
    session_replay_url = models.URLField(blank=True, default="",
                                          help_text="Recording or replay link if permitted.")
    transcript_url = models.URLField(blank=True, default="",
                                      help_text="AI-generated transcript if enabled and consented.")
    transcript_consent = models.BooleanField(default=False,
                                              help_text="Both parties consented to transcript.")

    # Session workspace
    shared_notes = models.TextField(blank=True, default="",
                                     help_text="Collaborative notes visible to both parties.")
    whiteboard_url = models.URLField(blank=True, default="")
    provider_private_notes = models.TextField(blank=True, default="",
                                               help_text="Provider-only internal notes.")
    post_session_summary = models.TextField(blank=True, default="",
                                             help_text="AI-assisted or manual session summary.")

    # Post-session follow-up
    follow_up_sent = models.BooleanField(default=False)
    follow_up_sent_at = models.DateTimeField(null=True, blank=True)
    next_session_recommended = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_session"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session for {self.booking.reference} — {self.status}"


class SessionNote(models.Model):
    """Timestamped notes shared or private within a session."""

    class NoteType(models.TextChoices):
        SHARED = "shared", "Shared (Both Parties)"
        PROVIDER = "provider", "Provider Only"
        BUYER = "buyer", "Buyer Only"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    note_type = models.CharField(max_length=10, choices=NoteType.choices, default=NoteType.SHARED)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_session_note"
        ordering = ["created_at"]

    def __str__(self):
        return f"Note ({self.note_type}) in {self.session}"


class SessionDeliverable(models.Model):
    """
    Files, documents, and deliverables shared during or after a session.
    Used for resume markups, feedback docs, resources, etc.
    """

    class DeliverableType(models.TextChoices):
        RESUME_MARKUP = "resume_markup", "Annotated Resume"
        LINKEDIN_MARKUP = "linkedin_markup", "LinkedIn Feedback Doc"
        FEEDBACK_DOC = "feedback_doc", "Feedback Document"
        RESOURCE = "resource", "Resource / Reference Material"
        RECORDING = "recording", "Session Recording"
        TRANSCRIPT = "transcript", "Session Transcript"
        ASSIGNMENT = "assignment", "Assignment / Homework"
        CERTIFICATE = "certificate", "Completion Certificate"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="deliverables")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    deliverable_type = models.CharField(max_length=20, choices=DeliverableType.choices)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    file_url = models.URLField(help_text="Secure file storage URL.")
    file_name = models.CharField(max_length=200, blank=True, default="")
    file_size_kb = models.IntegerField(default=0)
    is_visible_to_buyer = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_session_deliverable"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.deliverable_type}) — {self.session}"


class SessionFeedbackForm(models.Model):
    """
    Post-session feedback from buyer or provider.
    Used for both structured ratings and free-form feedback.
    """

    class FeedbackSource(models.TextChoices):
        BUYER = "buyer", "Buyer Feedback"
        PROVIDER = "provider", "Provider Feedback"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="feedback_forms")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    source = models.CharField(max_length=10, choices=FeedbackSource.choices)

    # Dimensions (1–5 scale)
    overall_rating = models.IntegerField(default=0)
    helpfulness = models.IntegerField(default=0)
    clarity = models.IntegerField(default=0)
    expertise = models.IntegerField(default=0)
    punctuality = models.IntegerField(default=0)
    value_for_money = models.IntegerField(default=0)

    written_feedback = models.TextField(blank=True, default="")
    outcome_tags = models.JSONField(default=list,
                                     help_text="e.g. ['got_interview', 'improved_resume', 'clarity']")
    would_rebook = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_session_feedback"
        unique_together = [["session", "submitted_by"]]

    def __str__(self):
        return f"Feedback by {self.source} for {self.session}"


class SessionActionPlan(models.Model):
    """Action plan co-created between provider and buyer during/after a session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name="action_plan")
    title = models.CharField(max_length=300, default="My Action Plan")
    summary = models.TextField(blank=True, default="")
    goals = models.JSONField(default=list)
    resources = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_session_action_plan"

    def __str__(self):
        return f"Action Plan — {self.session}"


class SessionMilestone(models.Model):
    """Individual milestone on a session action plan."""

    class MilestoneStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_plan = models.ForeignKey(SessionActionPlan, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=MilestoneStatus.choices, default=MilestoneStatus.PENDING)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_session_milestone"
        ordering = ["sort_order", "due_date"]

    def __str__(self):
        return f"{self.title} — {self.status}"


class SessionAssignment(models.Model):
    """Homework/assignment given to the buyer by the provider."""

    class AssignmentStatus(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        OVERDUE = "overdue", "Overdue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=300)
    instructions = models.TextField()
    due_date = models.DateField(null=True, blank=True)
    submission_url = models.URLField(blank=True, default="")
    submission_notes = models.TextField(blank=True, default="")
    provider_feedback = models.TextField(blank=True, default="")
    status = models.CharField(max_length=15, choices=AssignmentStatus.choices, default=AssignmentStatus.ASSIGNED)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_session_assignment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Assignment: {self.title} ({self.status})"


class MockInterviewRubric(models.Model):
    """Structured scoring rubric for mock interview sessions."""

    class RubricLevel(models.TextChoices):
        POOR = "1", "1 – Poor"
        BELOW_AVERAGE = "2", "2 – Below Average"
        AVERAGE = "3", "3 – Average"
        GOOD = "4", "4 – Good"
        EXCELLENT = "5", "5 – Excellent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name="mock_interview_rubric")
    job_role = models.CharField(max_length=200, blank=True, default="")
    job_description = models.TextField(blank=True, default="")

    # Dimensions (1–5)
    communication_score = models.IntegerField(default=0)
    technical_score = models.IntegerField(default=0)
    problem_solving_score = models.IntegerField(default=0)
    cultural_fit_score = models.IntegerField(default=0)
    confidence_score = models.IntegerField(default=0)
    overall_score = models.IntegerField(default=0)

    strengths = models.TextField(blank=True, default="")
    areas_to_improve = models.TextField(blank=True, default="")
    recommended_resources = models.JSONField(default=list)
    would_hire_recommendation = models.CharField(max_length=20, blank=True, default="",
                                                   help_text="yes / probably_yes / no / not_yet")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_mock_interview_rubric"

    def __str__(self):
        return f"Rubric for {self.session}"


class AsyncReviewDelivery(models.Model):
    """
    Async review workflow: buyer submits document → provider reviews → delivers markup.
    """

    class ReviewStatus(models.TextChoices):
        SUBMITTED = "submitted", "Submitted by Buyer"
        IN_REVIEW = "in_review", "Under Review"
        DELIVERED = "delivered", "Review Delivered"
        REVISION_REQUESTED = "revision_requested", "Revision Requested"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name="async_review")
    submitted_document_url = models.URLField(help_text="Document submitted by buyer.")
    submitted_at = models.DateTimeField(null=True, blank=True)
    review_status = models.CharField(max_length=25, choices=ReviewStatus.choices, default=ReviewStatus.SUBMITTED)
    reviewed_document_url = models.URLField(blank=True, default="",
                                             help_text="Marked-up document delivered by provider.")
    video_review_url = models.URLField(blank=True, default="",
                                        help_text="Optional screen-recording review.")
    written_review = models.TextField(blank=True, default="")
    delivered_at = models.DateTimeField(null=True, blank=True)
    due_by = models.DateTimeField(null=True, blank=True,
                                   help_text="Provider's delivery deadline based on turnaround SLA.")

    class Meta:
        db_table = "mp_async_review"

    def __str__(self):
        return f"Async Review {self.review_status} — {self.session}"
