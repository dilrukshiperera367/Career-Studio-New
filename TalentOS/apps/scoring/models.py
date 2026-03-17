"""Scoring app models — Batch scoring for companies + individual scoring for candidates + interview scorecards."""

import uuid
import hashlib
from django.conf import settings
from django.db import models


# ===========================================================================
# INTERVIEW SCORECARDS (DB-backed, replaces in-memory scorecard_api.py)
# ===========================================================================

class ScorecardTemplate(models.Model):
    """Reusable interview scorecard template defining evaluation criteria."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="scorecard_templates",
        null=True, blank=True,
    )
    name = models.CharField(max_length=200)
    criteria = models.JSONField(
        default=list,
        help_text="List of criteria dicts: [{name, weight, description}]",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="scorecard_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scorecard_templates"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Scorecard(models.Model):
    """Structured interview scorecard submitted by an interviewer for an application."""

    RECOMMENDATION_CHOICES = [
        ("strong_yes", "Strong Yes"),
        ("yes", "Yes"),
        ("maybe", "Maybe"),
        ("no", "No"),
        ("strong_no", "Strong No"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="scorecards",
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submitted_scorecards",
    )
    template = models.ForeignKey(
        ScorecardTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="submissions",
    )
    interview_date = models.DateTimeField(help_text="When the interview took place")
    overall_score = models.IntegerField(help_text="1-5 overall rating")
    technical_score = models.IntegerField(null=True, blank=True, help_text="1-5 technical skills")
    communication_score = models.IntegerField(null=True, blank=True, help_text="1-5 communication")
    culture_fit_score = models.IntegerField(null=True, blank=True, help_text="1-5 culture fit")
    notes = models.TextField(blank=True, default="")
    recommendation = models.CharField(
        max_length=20, choices=RECOMMENDATION_CHOICES, default="yes",
    )
    # Stores any extra per-criteria scores beyond the standard four fields
    extra_scores = models.JSONField(
        default=dict, blank=True,
        help_text="Additional per-criteria scores: {criteria_name: score}",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scorecards"
        ordering = ["-created_at"]
        unique_together = [("application", "interviewer")]
        indexes = [
            models.Index(fields=["application"]),
            models.Index(fields=["interviewer"]),
        ]

    def __str__(self):
        return (
            f"Scorecard by {self.interviewer_id} | app={self.application_id} | "
            f"score={self.overall_score} | rec={self.recommendation}"
        )


# ===========================================================================
# COMPANY: Batch Scoring
# ===========================================================================

class JobScoreBatch(models.Model):
    """A scoring batch: one JD + many CVs."""

    STATUS_CHOICES = [
        ("created", "Created"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="score_batches",
    )
    job_title = models.CharField(max_length=300, blank=True, default="")
    jd_text = models.TextField(help_text="Raw job description text")
    jd_requirements_json = models.JSONField(
        default=dict, blank=True,
        help_text="Extracted requirements: skills, years, location, etc.",
    )
    scoring_weights = models.JSONField(
        default=dict, blank=True,
        help_text="Custom weights override: {content, title, experience, recency, format}",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_batches",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    total_items = models.IntegerField(default=0)
    parsed_items = models.IntegerField(default=0)
    scored_items = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_score_batches"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch: {self.job_title or 'Untitled'} ({self.status})"


class BatchItem(models.Model):
    """A single CV within a scoring batch."""

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("parsing", "Parsing"),
        ("parsed", "Parsed"),
        ("scoring", "Scoring"),
        ("done", "Done"),
        ("failed", "Failed"),
        ("duplicate", "Duplicate"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        JobScoreBatch, on_delete=models.CASCADE, related_name="items",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="batch_items",
    )
    file_name = models.CharField(max_length=500)
    file = models.FileField(
        upload_to="batches/%Y/%m/",
        null=True,
        blank=True,
        help_text="CV file stored in S3/MinIO (replaces BinaryField)",
    )
    file_type = models.CharField(max_length=10, default="pdf")  # pdf, docx
    file_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    raw_text = models.TextField(blank=True, default="")
    parsed_json = models.JSONField(default=dict, blank=True)
    candidate_name = models.CharField(max_length=300, blank=True, default="")
    candidate_email = models.CharField(max_length=300, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "batch_items"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} ({self.status})"

    def compute_hash(self):
        """SHA256 hash of file content for dedup."""
        if self.file:
            self.file.seek(0)
            content = self.file.read()
            self.file.seek(0)
            self.file_hash = hashlib.sha256(content).hexdigest()


class BatchItemScore(models.Model):
    """Score result for a single CV in a batch."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_item = models.OneToOneField(
        BatchItem, on_delete=models.CASCADE, related_name="score",
    )
    score_total = models.IntegerField(default=0, help_text="0-100 ATS score")
    content_score = models.FloatField(default=0, help_text="0-1 content match")
    title_score = models.FloatField(default=0, help_text="0-1 title alignment")
    experience_score = models.FloatField(default=0, help_text="0-1 experience fit")
    recency_score = models.FloatField(default=0, help_text="0-1 recency")
    format_score = models.FloatField(default=0, help_text="0-1 format quality")
    breakdown_json = models.JSONField(
        default=dict, blank=True,
        help_text="Full breakdown: matched/missing skills, evidence, penalties",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "batch_item_scores"

    def __str__(self):
        return f"Score: {self.score_total}/100 for {self.batch_item.file_name}"


# ===========================================================================
# CANDIDATE: Personal Scoring
# ===========================================================================

class CandidateProfile(models.Model):
    """Extra profile info for candidate users."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_profile",
    )
    headline = models.CharField(max_length=300, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "candidate_profiles"

    def __str__(self):
        return f"Profile: {self.user.email}"


class CandidateResumeVersion(models.Model):
    """Versioned resume storage for candidates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resume_versions",
    )
    file_name = models.CharField(max_length=500)
    file = models.FileField(
        upload_to="resumes/%Y/%m/",
        null=True,
        blank=True,
        help_text="Resume file stored in S3/MinIO (replaces BinaryField)",
    )
    file_type = models.CharField(max_length=10, default="pdf")
    raw_text = models.TextField(blank=True, default="")
    parsed_json = models.JSONField(default=dict, blank=True)
    version_label = models.CharField(max_length=100, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_resume_versions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} v{self.version_label or self.created_at}"


class CandidateScoreRun(models.Model):
    """A single score run: candidate CV + JD → score."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="score_runs",
    )
    resume_version = models.ForeignKey(
        CandidateResumeVersion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="score_runs",
    )
    jd_text = models.TextField(help_text="Job description used for scoring")
    jd_title = models.CharField(max_length=300, blank=True, default="")
    jd_requirements_json = models.JSONField(default=dict, blank=True)
    score_total = models.IntegerField(default=0)
    content_score = models.FloatField(default=0)
    title_score = models.FloatField(default=0)
    experience_score = models.FloatField(default=0)
    recency_score = models.FloatField(default=0)
    format_score = models.FloatField(default=0)
    breakdown_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_score_runs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Score: {self.score_total}/100 ({self.jd_title or 'Untitled JD'})"
