"""Marketplace Search — personalized feeds, job recommendations, browse surfaces, ranking explanations."""
import uuid
from django.db import models
from django.conf import settings


class PersonalizedFeed(models.Model):
    """Cached ranked job feed per user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personalized_feeds")
    job_ids = models.JSONField(default=list, help_text="Ordered list of job UUIDs in ranked order")
    algorithm_version = models.CharField(max_length=20, default="v1")
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jf_personalized_feeds"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Feed for {self.user} ({self.algorithm_version})"


class JobRecommendation(models.Model):
    """Recommended jobs for a seeker (similar, also-viewed, role-adjacent)."""
    class RecommendationType(models.TextChoices):
        SIMILAR = "similar", "Similar Jobs"
        ALSO_VIEWED = "also_viewed", "People Also Viewed"
        ROLE_ADJACENT = "role_adjacent", "Related Roles"
        TRENDING = "trending", "Trending"
        PERSONALIZED = "personalized", "For You"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_job = models.ForeignKey(
        "jobs.JobListing", on_delete=models.CASCADE,
        related_name="recommendations_as_source", null=True, blank=True
    )
    recommended_job = models.ForeignKey(
        "jobs.JobListing", on_delete=models.CASCADE,
        related_name="recommendations_as_target"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             null=True, blank=True, related_name="job_recommendations")
    rec_type = models.CharField(max_length=20, choices=RecommendationType.choices)
    score = models.FloatField(default=0.0, help_text="Recommendation relevance score")
    reasons = models.JSONField(default=list, help_text="Human-readable reasons e.g. ['same category', 'similar salary']")
    algorithm_version = models.CharField(max_length=20, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_job_recommendations"
        ordering = ["-score"]
        indexes = [
            models.Index(fields=["source_job", "rec_type"], name="idx_rec_source"),
            models.Index(fields=["user", "rec_type"], name="idx_rec_user"),
        ]

    def __str__(self):
        return f"{self.rec_type}: {self.source_job} → {self.recommended_job}"


class SearchExplanation(models.Model):
    """Explains why a job appears in a search result for a specific user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="search_explanations")
    job = models.ForeignKey("jobs.JobListing", on_delete=models.CASCADE, related_name="explanations")
    matching_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    match_score = models.FloatField(default=0.0)
    salary_match = models.BooleanField(default=False)
    location_match = models.BooleanField(default=False)
    experience_match = models.BooleanField(default=False)
    explanation_text = models.CharField(max_length=500, blank=True, default="")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_search_explanations"
        unique_together = ["user", "job"]

    def __str__(self):
        return f"Explanation: {self.user} × {self.job} ({self.match_score:.0%})"


class BrowseSurface(models.Model):
    """Pre-computed browse lane for category/city/salary/level navigation."""
    class SurfaceType(models.TextChoices):
        CATEGORY = "category", "Browse by Category"
        CITY = "city", "Browse by City"
        SALARY = "salary", "Browse by Salary"
        LEVEL = "level", "Browse by Level"
        INDUSTRY = "industry", "Browse by Industry"
        SHIFT = "shift", "Browse by Shift"
        CONTRACT = "contract", "Browse by Contract Type"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    surface_type = models.CharField(max_length=15, choices=SurfaceType.choices)
    label = models.CharField(max_length=100)
    label_si = models.CharField(max_length=100, blank=True, default="")
    label_ta = models.CharField(max_length=100, blank=True, default="")
    slug = models.SlugField(max_length=100)
    job_count = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_browse_surfaces"
        ordering = ["-is_featured", "sort_order"]
        unique_together = ["surface_type", "slug"]

    def __str__(self):
        return f"{self.get_surface_type_display()}: {self.label} ({self.job_count})"


class TrendingEmployer(models.Model):
    """Weekly snapshot of trending/hiring employers."""
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="trending_snapshots")
    week_start = models.DateField()
    job_post_velocity = models.IntegerField(default=0, help_text="New jobs this week")
    view_growth_pct = models.FloatField(default=0.0)
    application_growth_pct = models.FloatField(default=0.0)
    trending_score = models.FloatField(default=0.0)
    reasons = models.JSONField(default=list)

    class Meta:
        db_table = "jf_trending_employers"
        unique_together = ["employer", "week_start"]
        ordering = ["-trending_score"]

    def __str__(self):
        return f"{self.employer} trending week {self.week_start}"
