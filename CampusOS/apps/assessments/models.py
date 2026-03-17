"""CampusOS — Assessments models."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class AssessmentBundle(TimestampedModel):
    """A campus-configured assessment (aptitude, technical, behavioural, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="assessment_bundles")
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)

    ASSESSMENT_TYPE_CHOICES = [
        ("aptitude", "Aptitude Test"),
        ("technical", "Technical Assessment"),
        ("personality", "Personality / Behavioural"),
        ("coding", "Coding Challenge"),
        ("verbal", "Verbal Reasoning"),
        ("domain", "Domain Knowledge"),
        ("mock_interview", "Mock Interview"),
        ("custom", "Custom"),
    ]

    title = models.CharField(max_length=250)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    total_marks = models.PositiveSmallIntegerField(default=100)
    pass_marks = models.PositiveSmallIntegerField(default=40)
    number_of_questions = models.PositiveSmallIntegerField(default=0)
    is_proctored = models.BooleanField(default=False)
    is_randomized = models.BooleanField(default=True)
    allow_back_navigation = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    target_programs = models.ManyToManyField("campus.Program", blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class AssessmentSchedule(TimestampedModel):
    """A specific sitting/window for an AssessmentBundle."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bundle = models.ForeignKey(AssessmentBundle, on_delete=models.CASCADE, related_name="schedules")
    drive = models.ForeignKey(
        "placements.PlacementDrive", null=True, blank=True, on_delete=models.SET_NULL, related_name="assessment_schedules"
    )
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    venue = models.CharField(max_length=200, blank=True)
    max_attempts = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["window_start"]


class StudentAssessmentAttempt(TimestampedModel):
    """A student's attempt at an scheduled assessment."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(AssessmentSchedule, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="assessment_attempts")

    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("submitted", "Submitted"),
        ("evaluated", "Evaluated"),
        ("absent", "Absent"),
        ("cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="not_started")
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_pass = models.BooleanField(null=True, blank=True)
    section_scores = models.JSONField(default=dict, help_text="e.g. {aptitude: 35, verbal: 28}")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    browser_fingerprint = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = [["schedule", "student"]]
        ordering = ["-created_at"]


class ProctorFlag(TimestampedModel):
    """Flag raised during a proctored assessment attempt."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(StudentAssessmentAttempt, on_delete=models.CASCADE, related_name="proctor_flags")

    FLAG_TYPE_CHOICES = [
        ("tab_switch", "Tab Switch Detected"),
        ("face_not_detected", "Face Not Detected"),
        ("multiple_faces", "Multiple Faces Detected"),
        ("screen_capture", "Screen Capture Attempt"),
        ("fullscreen_exit", "Fullscreen Exit"),
        ("copy_paste", "Copy/Paste Detected"),
        ("suspicious_device", "Suspicious Device"),
        ("manual", "Manual Flag by Proctor"),
    ]

    flag_type = models.CharField(max_length=25, choices=FLAG_TYPE_CHOICES)
    flagged_at = models.DateTimeField(auto_now_add=True)
    screenshot_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    action_taken = models.CharField(
        max_length=20,
        choices=[("dismissed", "Dismissed"), ("warned", "Warned"), ("disqualified", "Disqualified")],
        blank=True,
    )

    class Meta:
        ordering = ["-flagged_at"]


class CampusBenchmarkScore(TimestampedModel):
    """Rolling benchmark stats for an assessment bundle at campus/program level."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bundle = models.ForeignKey(AssessmentBundle, on_delete=models.CASCADE, related_name="benchmarks")
    program = models.ForeignKey("campus.Program", null=True, blank=True, on_delete=models.SET_NULL)
    as_of_date = models.DateField()
    total_attempts = models.PositiveIntegerField(default=0)
    avg_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pass_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    top_quartile_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [["bundle", "program", "as_of_date"]]
        ordering = ["-as_of_date"]
