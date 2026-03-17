"""CampusOS — Alumni Mentors models."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class AlumniProfile(TimestampedModel):
    """Extended profile for alumni who return as mentors."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="alumni_profile")
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="alumni_profiles")

    # Graduation details
    graduation_year = models.PositiveSmallIntegerField()
    program_studied = models.ForeignKey("campus.Program", null=True, blank=True, on_delete=models.SET_NULL)
    student_roll = models.CharField(max_length=50, blank=True)

    # Professional info
    current_employer = models.CharField(max_length=200, blank=True)
    current_designation = models.CharField(max_length=200, blank=True)
    current_industry = models.CharField(max_length=100, blank=True)
    current_city = models.CharField(max_length=100, blank=True)
    current_country = models.CharField(max_length=100, default="Sri Lanka")
    linkedin_url = models.URLField(blank=True)
    total_experience_years = models.PositiveSmallIntegerField(default=0)

    # Mentor availability
    is_mentor = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    mentoring_capacity = models.PositiveSmallIntegerField(default=2, help_text="Max concurrent mentees")
    mentoring_areas = models.JSONField(default=list, help_text="List of topic strings")
    available_slots_per_week = models.PositiveSmallIntegerField(default=1)
    preferred_meeting_mode = models.CharField(
        max_length=20,
        choices=[("video", "Video Call"), ("chat", "Chat"), ("phone", "Phone"), ("in_person", "In Person")],
        default="video",
    )
    bio_for_students = models.TextField(blank=True)
    mentor_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    total_sessions_completed = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-graduation_year"]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.graduation_year})"


class MentorRequest(TimestampedModel):
    """Student requests a mentor."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    ]

    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="mentor_requests")
    mentor = models.ForeignKey(AlumniProfile, on_delete=models.CASCADE, related_name="mentor_requests")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    message = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    preferred_duration_weeks = models.PositiveSmallIntegerField(default=8)
    rejection_note = models.TextField(blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["student", "mentor"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} → {self.mentor} [{self.status}]"


class MentorSession(TimestampedModel):
    """A 1:1 mentor session log."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    mentorship = models.ForeignKey(MentorRequest, on_delete=models.CASCADE, related_name="sessions")
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    mode = models.CharField(
        max_length=20,
        choices=[("video", "Video"), ("chat", "Chat"), ("phone", "Phone"), ("in_person", "In Person")],
    )
    agenda = models.TextField(blank=True)
    notes_mentor = models.TextField(blank=True)
    notes_student = models.TextField(blank=True)
    student_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    mentor_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    cancelled_by = models.CharField(max_length=10, choices=[("mentor", "Mentor"), ("student", "Student")], blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-scheduled_at"]


class MentorshipGoal(TimestampedModel):
    """Tracks goals set within a mentorship relationship."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mentorship = models.ForeignKey(MentorRequest, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    is_achieved = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(null=True, blank=True)


class GroupMentoringCircle(TimestampedModel):
    """Alumni-led group session (up to ~10 students)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="mentoring_circles")
    host = models.ForeignKey(AlumniProfile, on_delete=models.CASCADE, related_name="circles_hosted")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    topic_tags = models.JSONField(default=list)
    scheduled_at = models.DateTimeField()
    max_participants = models.PositiveSmallIntegerField(default=10)
    meeting_link = models.URLField(blank=True)
    is_public = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["scheduled_at"]


class CircleEnrollment(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(GroupMentoringCircle, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="circle_enrollments")
    attended = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = [["circle", "student"]]


class AlumniJobShare(TimestampedModel):
    """Alumni shares a job/opportunity with campus students."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE)
    shared_by = models.ForeignKey(AlumniProfile, on_delete=models.CASCADE, related_name="job_shares")
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    opportunity_type = models.CharField(
        max_length=20,
        choices=[("job", "Full-time Job"), ("internship", "Internship"), ("referral", "Referral"), ("contract", "Contract")],
        default="job",
    )
    description = models.TextField(blank=True)
    apply_url = models.URLField(blank=True)
    expires_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
