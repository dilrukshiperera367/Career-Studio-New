"""CampusOS — Advisors & Faculty Workspace models."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class AdvisorProfile(TimestampedModel):
    """Faculty/career-advisor profile with workload settings."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="advisor_profile")
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="advisors")
    department = models.ForeignKey("campus.Department", null=True, blank=True, on_delete=models.SET_NULL)
    designation = models.CharField(max_length=200, blank=True)
    max_caseload = models.PositiveSmallIntegerField(default=30)
    specializations = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name()


class AdvisorStudentMapping(TimestampedModel):
    """Assigns students to an advisor."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advisor = models.ForeignKey(AdvisorProfile, on_delete=models.CASCADE, related_name="student_mappings")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="advisor_mappings")
    academic_year = models.ForeignKey("campus.AcademicYear", null=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [["advisor", "student", "academic_year"]]


class StudentNote(TimestampedModel):
    """Private advisor note about a student."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advisor = models.ForeignKey(AdvisorProfile, on_delete=models.CASCADE, related_name="student_notes")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="advisor_notes")
    note_type = models.CharField(
        max_length=30,
        choices=[
            ("general", "General"),
            ("academic", "Academic Concern"),
            ("career", "Career Counselling"),
            ("behavioural", "Behavioural"),
            ("intervention", "Intervention"),
            ("reference", "Reference Letter"),
            ("follow_up", "Follow-Up"),
        ],
        default="general",
    )
    content = models.TextField()
    is_flagged = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True, help_text="Not visible to other advisors")
    follow_up_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ResumeApprovalRequest(TimestampedModel):
    """Student submits resume for advisor approval before applying to drives."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="resume_approval_requests")
    advisor = models.ForeignKey(AdvisorProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="resume_reviews")

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("revision_needed", "Revision Needed"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    resume_version_url = models.URLField()
    advisor_comments = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Advisor quality score 0-100")

    class Meta:
        ordering = ["-created_at"]


class InterventionAlert(TimestampedModel):
    """System or advisor-raised alert for at-risk student intervention."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="intervention_alerts")
    created_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="alerts_created"
    )
    assigned_to = models.ForeignKey(AdvisorProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_alerts")

    ALERT_TYPE_CHOICES = [
        ("low_readiness", "Low Readiness Score"),
        ("no_applications", "No Applications Submitted"),
        ("profile_incomplete", "Incomplete Profile"),
        ("semester_risk", "Semester-end Risk"),
        ("no_internship", "No Internship by Deadline"),
        ("mentor_dropout", "Mentor Dropout"),
        ("custom", "Custom"),
    ]
    SEVERITY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]

    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="medium")
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("in_progress", "In Progress"), ("resolved", "Resolved")],
        default="open",
    )
    resolution_note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
