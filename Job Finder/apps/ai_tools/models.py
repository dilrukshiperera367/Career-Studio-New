"""AI Tools app — cover letters, LinkedIn analysis, interview prep,
mentorship, networking drafts, brand score, career roadmap.
"""
import uuid
from django.db import models
from django.conf import settings


# ── Cover Letters ─────────────────────────────────────────────────────────────

class CoverLetter(models.Model):
    """AI-generated cover letter."""

    class Tone(models.TextChoices):
        PROFESSIONAL = "professional", "Professional"
        ENTHUSIASTIC = "enthusiastic", "Enthusiastic"
        CONFIDENT = "confident", "Confident"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="cover_letters"
    )
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    job_description = models.TextField(blank=True, default="")
    your_name = models.CharField(max_length=200)
    your_skills = models.JSONField(default=list)
    experience = models.CharField(max_length=500, blank=True, default="")
    tone = models.CharField(max_length=15, choices=Tone.choices, default=Tone.PROFESSIONAL)
    content = models.TextField()
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_cover_letters"
        ordering = ["-created_at"]


# ── LinkedIn Analysis ─────────────────────────────────────────────────────────

class LinkedInAnalysis(models.Model):
    """LinkedIn profile optimization analysis."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="linkedin_analyses"
    )
    headline = models.CharField(max_length=300, blank=True, default="")
    total_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    sections = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_linkedin_analyses"
        ordering = ["-created_at"]


# ── Interview Prep ────────────────────────────────────────────────────────────

class InterviewPrepSession(models.Model):
    """Practice interview session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="interview_sessions"
    )
    role = models.CharField(max_length=100)
    total_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=25)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_interview_sessions"
        ordering = ["-created_at"]


class InterviewAnswer(models.Model):
    """Answer to an interview question."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        InterviewPrepSession, on_delete=models.CASCADE, related_name="answers"
    )
    question_id = models.CharField(max_length=20)
    answer = models.TextField()
    score = models.IntegerField(default=0)
    feedback = models.JSONField(default=list)
    time_taken_seconds = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_interview_answers"


# ── Mentorship ────────────────────────────────────────────────────────────────

class MentorProfile(models.Model):
    """Mentor available for matching."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="mentor_profile", null=True, blank=True
    )
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True, default="")
    industry = models.CharField(max_length=100, blank=True, default="")
    district = models.ForeignKey(
        "taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True
    )
    skills = models.JSONField(default=list)
    bio = models.TextField(blank=True, default="")
    years_experience = models.IntegerField(default=0)
    hourly_rate_lkr = models.IntegerField(default=0)  # 0 = free
    is_available = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    sessions_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_mentor_profiles"
        ordering = ["-rating"]

    def __str__(self):
        return self.name


class MentorshipRequest(models.Model):
    """Request from seeker to mentor."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mentor = models.ForeignKey(
        MentorProfile, on_delete=models.CASCADE, related_name="requests"
    )
    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="mentorship_requests"
    )
    message = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_mentorship_requests"
        ordering = ["-created_at"]


# ── Networking Drafts ─────────────────────────────────────────────────────────

class NetworkingDraft(models.Model):
    """Saved networking message draft."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="networking_drafts"
    )
    template_type = models.CharField(max_length=50)
    recipient_name = models.CharField(max_length=200, blank=True, default="")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_networking_drafts"
        ordering = ["-created_at"]


# ── Brand Score ───────────────────────────────────────────────────────────────

class BrandScore(models.Model):
    """Profile brand score snapshot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="brand_scores"
    )
    total_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    grade = models.CharField(max_length=2, default="D")
    sections = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_brand_scores"
        ordering = ["-computed_at"]


# ── Career Roadmap ────────────────────────────────────────────────────────────

class CareerRoadmap(models.Model):
    """Career transition roadmap with milestones."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="career_roadmaps"
    )
    title = models.CharField(max_length=200)
    target_role = models.CharField(max_length=200)
    target_salary = models.CharField(max_length=50, blank=True, default="")
    timeframe = models.CharField(max_length=50, blank=True, default="")
    milestones = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_ai_career_roadmaps"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
