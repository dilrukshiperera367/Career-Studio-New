"""Job Quality — freshness scoring, duplicate detection, scam risk, quality scoring."""
import uuid
from django.db import models


class JobQualityScore(models.Model):
    """Quality, freshness, and scam risk score per job listing."""
    class ScamRisk(models.TextChoices):
        NONE = "none", "No Risk"
        LOW = "low", "Low Risk"
        MEDIUM = "medium", "Medium Risk"
        HIGH = "high", "High Risk"
        FLAGGED = "flagged", "Flagged as Scam"

    job = models.OneToOneField("jobs.JobListing", on_delete=models.CASCADE, related_name="quality_score_obj")
    overall_score = models.FloatField(default=0.0, help_text="0.0–100.0 overall quality")
    freshness_score = models.FloatField(default=0.0, help_text="0.0–100.0 freshness (recency + activity)")
    completeness_score = models.FloatField(default=0.0, help_text="0.0–100.0 field completeness")
    trust_score = models.FloatField(default=0.0, help_text="0.0–100.0 employer trust contribution")
    scam_risk = models.CharField(max_length=10, choices=ScamRisk.choices, default=ScamRisk.NONE)
    scam_signals = models.JSONField(default=list, help_text="Detected scam signal descriptions")
    has_salary = models.BooleanField(default=False)
    has_requirements = models.BooleanField(default=False)
    has_benefits = models.BooleanField(default=False)
    is_duplicate = models.BooleanField(default=False)
    duplicate_group_id = models.UUIDField(null=True, blank=True)
    last_scored_at = models.DateTimeField(auto_now=True)
    score_version = models.CharField(max_length=10, default="v1")

    class Meta:
        db_table = "jf_job_quality_scores"

    def __str__(self):
        return f"Quality {self.job}: {self.overall_score:.1f} / scam={self.scam_risk}"


class DuplicateJobGroup(models.Model):
    """Groups of job listings detected as duplicates of each other."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_job = models.ForeignKey(
        "jobs.JobListing", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="duplicate_group_as_canonical"
    )
    job_ids = models.JSONField(default=list, help_text="All duplicate job UUIDs in this group")
    detection_method = models.CharField(max_length=30, default="title_similarity")
    similarity_score = models.FloatField(default=0.0)
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_duplicate_job_groups"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DupGroup {self.id}: {len(self.job_ids)} jobs"


class ScamPattern(models.Model):
    """Known scam patterns — keywords, phrases, domain patterns."""
    class PatternType(models.TextChoices):
        KEYWORD = "keyword", "Keyword"
        REGEX = "regex", "Regular Expression"
        DOMAIN = "domain", "Domain Pattern"
        PHRASE = "phrase", "Phrase"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pattern_type = models.CharField(max_length=10, choices=PatternType.choices)
    pattern = models.CharField(max_length=500)
    description = models.CharField(max_length=300, blank=True, default="")
    risk_level = models.CharField(max_length=10,
                                  choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                                  default="medium")
    is_active = models.BooleanField(default=True)
    hit_count = models.IntegerField(default=0)
    created_by_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_scam_patterns"
        ordering = ["-hit_count"]

    def __str__(self):
        return f"[{self.pattern_type}] {self.pattern[:60]}"


class FreshnessSignal(models.Model):
    """Tracks repost and edit events affecting job freshness."""
    class SignalType(models.TextChoices):
        POSTED = "posted", "Initial Post"
        BOOSTED = "boosted", "Manually Boosted"
        REPOSTED = "reposted", "Reposted"
        EDITED = "edited", "Job Edited"
        EXPIRED = "expired", "Expired"
        RENEWED = "renewed", "Renewed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("jobs.JobListing", on_delete=models.CASCADE, related_name="freshness_signals")
    signal_type = models.CharField(max_length=10, choices=SignalType.choices)
    freshness_delta = models.FloatField(default=0.0, help_text="Score change from this signal")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_freshness_signals"
        ordering = ["-created_at"]
