"""Marketplace Analytics — supply/demand, funnel tracking, employer ROI, marketplace health."""
import uuid
from django.db import models
from django.conf import settings


class MarketplaceLiquiditySnapshot(models.Model):
    """Daily supply vs demand snapshot per category and district."""
    date = models.DateField()
    category = models.ForeignKey("taxonomy.JobCategory", on_delete=models.CASCADE,
                                 related_name="liquidity_snapshots")
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="liquidity_snapshots")
    active_jobs = models.IntegerField(default=0, help_text="Supply: active job count")
    seeker_searches = models.IntegerField(default=0, help_text="Demand: seekers searching in this segment")
    apply_count = models.IntegerField(default=0)
    demand_supply_ratio = models.FloatField(default=0.0,
                                            help_text="seekers_searching / active_jobs (>1 = under-supplied)")
    avg_time_to_fill_days = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "jf_marketplace_liquidity"
        unique_together = ["date", "category", "district"]
        ordering = ["-date"]

    def __str__(self):
        return f"Liquidity {self.date}: {self.category} / {self.district} — ratio {self.demand_supply_ratio:.2f}"


class FunnelEvent(models.Model):
    """Detailed funnel step tracking: search → view → save → apply → submit."""
    class Step(models.TextChoices):
        SEARCH = "search", "Job Search"
        JOB_VIEW = "job_view", "Job Detail View"
        JOB_SAVE = "job_save", "Job Saved"
        APPLY_START = "apply_start", "Apply Started"
        APPLY_SUBMIT = "apply_submit", "Application Submitted"
        COMPANY_VIEW = "company_view", "Company Page View"
        ALERT_OPEN = "alert_open", "Alert Email Opened"
        ALERT_CLICK = "alert_click", "Alert Email Clicked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=64, blank=True, default="")
    step = models.CharField(max_length=15, choices=Step.choices)
    job_id = models.UUIDField(null=True, blank=True)
    employer_id = models.UUIDField(null=True, blank=True)
    search_query = models.CharField(max_length=300, blank=True, default="")
    page_type = models.CharField(max_length=50, blank=True, default="")
    source_channel = models.CharField(max_length=50, blank=True, default="",
                                      help_text="organic/alert/saved/promoted/direct")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_funnel_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["step", "created_at"], name="idx_funnel_step_date"),
            models.Index(fields=["user", "step"], name="idx_funnel_user_step"),
        ]

    def __str__(self):
        return f"Funnel {self.step}: {self.user or 'anon'} @ {self.created_at.date()}"


class EmployerROISummary(models.Model):
    """Weekly employer ROI summary for the dashboard."""
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="roi_summaries")
    week_start = models.DateField()
    job_views = models.IntegerField(default=0)
    profile_views = models.IntegerField(default=0)
    applications = models.IntegerField(default=0)
    applications_quality_score = models.FloatField(default=0.0, help_text="0–100 quality of applicants")
    shortlisted = models.IntegerField(default=0)
    hired = models.IntegerField(default=0)
    avg_time_to_shortlist_hours = models.FloatField(null=True, blank=True)
    sponsored_impressions = models.IntegerField(default=0)
    sponsored_clicks = models.IntegerField(default=0)
    sponsored_spend_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    organic_applies = models.IntegerField(default=0)
    sponsored_applies = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_employer_roi_summaries"
        unique_together = ["employer", "week_start"]
        ordering = ["-week_start"]

    def __str__(self):
        return f"ROI: {self.employer} week {self.week_start}"


class MarketplaceHealthScore(models.Model):
    """Daily overall marketplace health composite score."""
    date = models.DateField(unique=True)
    overall_score = models.FloatField(default=0.0, help_text="0–100 composite health")
    job_supply_score = models.FloatField(default=0.0)
    seeker_demand_score = models.FloatField(default=0.0)
    apply_conversion_score = models.FloatField(default=0.0)
    employer_response_score = models.FloatField(default=0.0)
    trust_score = models.FloatField(default=0.0)
    fraud_rate = models.FloatField(default=0.0, help_text="% of jobs flagged as suspicious")
    duplicate_rate = models.FloatField(default=0.0)
    avg_apply_rate = models.FloatField(default=0.0, help_text="% of viewers who apply")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "jf_marketplace_health_scores"
        ordering = ["-date"]

    def __str__(self):
        return f"Health {self.date}: {self.overall_score:.1f}"
