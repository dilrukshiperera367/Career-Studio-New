"""Promotions & Ads — promoted jobs, ad clicks, sponsored company pages, campaign management."""
import uuid
from django.db import models
from django.conf import settings


class PromotedJobCampaign(models.Model):
    """An employer's ad campaign for promoting job listings."""
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class BidModel(models.TextChoices):
        CPC = "cpc", "Cost Per Click"
        CPAp = "cpa", "Cost Per Application"
        FIXED = "fixed", "Fixed Boost"
        DAILY_BUDGET = "daily_budget", "Daily Budget"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="ad_campaigns")
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    bid_model = models.CharField(max_length=15, choices=BidModel.choices, default=BidModel.CPC)
    bid_amount_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_budget_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_budget_lkr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    spent_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    applications = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_promoted_job_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Campaign: {self.name} ({self.status})"

    @property
    def ctr(self):
        return round(self.clicks / self.impressions * 100, 2) if self.impressions else 0

    @property
    def cpa(self):
        return round(float(self.spent_lkr) / self.applications, 2) if self.applications else 0


class PromotedJob(models.Model):
    """A specific job listing linked to a promotion campaign."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(PromotedJobCampaign, on_delete=models.CASCADE, related_name="promoted_jobs")
    job = models.ForeignKey("jobs.JobListing", on_delete=models.CASCADE, related_name="promotions")
    boost_factor = models.FloatField(default=2.0, help_text="Ranking multiplier")
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    applications = models.IntegerField(default=0)
    spent_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_promoted_jobs"
        unique_together = ["campaign", "job"]

    def __str__(self):
        return f"Promoted: {self.job} in {self.campaign}"


class AdClick(models.Model):
    """Tracks each ad click event for billing and analytics."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promoted_job = models.ForeignKey(PromotedJob, on_delete=models.CASCADE, related_name="click_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=64, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_unique = models.BooleanField(default=True)
    cost_lkr = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    source_page = models.CharField(max_length=100, blank=True, default="")
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_ad_clicks"
        indexes = [
            models.Index(fields=["promoted_job", "clicked_at"], name="idx_adclick_job_date"),
        ]


class SponsoredCompanyPage(models.Model):
    """Employer brand promotion slot (sponsored company page feature)."""
    class Placement(models.TextChoices):
        SEARCH_TOP = "search_top", "Top of Search Results"
        HOMEPAGE_FEATURED = "homepage_featured", "Homepage Featured"
        CATEGORY_SPOTLIGHT = "category_spotlight", "Category Spotlight"
        SIDEBAR = "sidebar", "Sidebar Banner"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="sponsored_placements")
    placement = models.CharField(max_length=25, choices=Placement.choices)
    headline = models.CharField(max_length=200, blank=True, default="")
    tagline = models.CharField(max_length=300, blank=True, default="")
    cta_text = models.CharField(max_length=100, blank=True, default="See Open Roles")
    cta_url = models.URLField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    budget_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    spent_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_sponsored_company_pages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sponsored: {self.employer} ({self.placement})"
