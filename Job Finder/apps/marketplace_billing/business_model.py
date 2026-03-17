"""
Job Finder — Multi-Engine Business Model Extension
===================================================
Extends apps/marketplace_billing/ with the full Job Finder revenue stack:

  Layer 1 – Recurring SaaS
    - JobPostPlan            : paid job posting packages (credits-per-cycle)
    - FeaturedEmployerPlan   : company branding subscription
    - ResumeDatabasePlan     : recruiter resume search subscription

  Layer 2 – Transactional
    - JobPostCredit          : single or bulk job post credit purchases
    - PromotedJobProduct     : per-listing promotion (homepage, top-of-search, email blast)
    - PromotedJobOrder       : employer purchases a promotion slot for a specific listing
    - CpcCampaign            : cost-per-click ad campaign tied to AdBudget wallet
    - CpaCampaign            : cost-per-application campaign
    - RecruiterMessagingPack : bulk messaging credits to contact candidates
    - ApplicantScreeningAddon: AI screening add-on per job post
    - ResponseRateAnalyticsPack : advanced analytics pack (per employer, per period)

  Layer 3 – Commerce & Services
    - SalaryReportSponsorship: employer sponsors a salary-benchmark report page
    - ResumeDbAccessRecord   : per-view or per-download CV access charge
    - JobFinderBillingEvent  : audit trail for all billing events

All pricing LKR-first. References existing models via string FKs to avoid
circular imports with the existing marketplace_billing models.
"""
import uuid
from django.db import models


# ---------------------------------------------------------------------------
# Layer 1 — Recurring SaaS Plans
# ---------------------------------------------------------------------------

class JobPostPlan(models.Model):
    """Subscription plan that bundles a set number of job post credits per cycle."""

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    price_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                    help_text="Foreign currency price — USD")
    job_credits_per_cycle = models.IntegerField(help_text="Number of job post credits granted each billing cycle")
    rollover_credits = models.BooleanField(default=False, help_text="Unused credits roll over to next cycle")
    max_active_jobs = models.IntegerField(default=-1, help_text="-1 = unlimited concurrent active listings")
    includes_featured_slots = models.IntegerField(default=0,
                                                  help_text="Complimentary featured/promoted listing slots per cycle")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_job_post_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_lkr}/{self.billing_cycle}"


class JobPostPlanSubscription(models.Model):
    """Employer subscription to a JobPostPlan."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRIAL = "trial", "Trial"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="jpp_subscriptions")
    plan = models.ForeignKey(JobPostPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    credits_remaining = models.IntegerField(default=0)
    started_at = models.DateTimeField()
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_job_post_plan_subscriptions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.employer} — {self.plan} ({self.status})"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE


class FeaturedEmployerPlan(models.Model):
    """Company branding / featured employer subscription plan."""

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    price_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Branding features included
    company_profile_badge = models.BooleanField(default=True,
                                                help_text="'Featured Employer' badge on profile and listings")
    homepage_logo_placement = models.BooleanField(default=False)
    email_newsletter_slot = models.BooleanField(default=False, help_text="Logo/mention in job alert newsletters")
    banner_ad_slots = models.IntegerField(default=0, help_text="Banner impressions per month")
    priority_listing_boost = models.BooleanField(default=False,
                                                 help_text="All active jobs boosted to top of search results")
    dedicated_company_page = models.BooleanField(default=False,
                                                 help_text="Custom landing page with culture content and media")
    analytics_dashboard = models.BooleanField(default=False,
                                              help_text="Branding campaign analytics dashboard access")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_featured_employer_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_lkr}/{self.billing_cycle}"


class FeaturedEmployerSubscription(models.Model):
    """Employer subscription to a FeaturedEmployerPlan."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="featured_employer_subs")
    plan = models.ForeignKey(FeaturedEmployerPlan, on_delete=models.PROTECT,
                             related_name="subscriptions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_featured_employer_subs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.employer} — {self.plan} ({self.status})"


class ResumeDatabasePlan(models.Model):
    """Recruiter resume database search subscription plan."""

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    price_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cv_views_per_month = models.IntegerField(default=50, help_text="-1 = unlimited")
    cv_downloads_per_month = models.IntegerField(default=10, help_text="-1 = unlimited; chargeable beyond quota")
    search_filters_advanced = models.BooleanField(default=False,
                                                  help_text="Access to advanced filters: skills, salary, location radius")
    saved_searches = models.IntegerField(default=5, help_text="Number of saved search alerts")
    recruiter_seats = models.IntegerField(default=1, help_text="Number of recruiter accounts under this plan")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_resume_db_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_lkr}/{self.billing_cycle}"


class ResumeDatabaseSubscription(models.Model):
    """Employer subscription to a ResumeDatabasePlan."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="resume_db_subs")
    plan = models.ForeignKey(ResumeDatabasePlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    cv_views_used = models.IntegerField(default=0)
    cv_downloads_used = models.IntegerField(default=0)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_resume_db_subs"
        ordering = ["-period_start"]

    def __str__(self):
        return f"{self.employer} — {self.plan} ({self.status})"

    @property
    def cv_views_remaining(self):
        if self.plan.cv_views_per_month == -1:
            return None  # unlimited
        return max(0, self.plan.cv_views_per_month - self.cv_views_used)


# ---------------------------------------------------------------------------
# Layer 2 — Transactional Revenue
# ---------------------------------------------------------------------------

class JobPostCredit(models.Model):
    """One-off or bulk job posting credit pack purchase (pay-as-you-go)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="job_post_credits")
    credits_purchased = models.IntegerField()
    credits_remaining = models.IntegerField()
    price_per_credit_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    total_paid_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Credits expire if unused by this date")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_job_post_credits"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employer} — {self.credits_remaining}/{self.credits_purchased} credits remaining"


class PromotedJobProduct(models.Model):
    """Catalog of available job promotion slot types."""

    class PromotionType(models.TextChoices):
        TOP_OF_SEARCH = "top_of_search", "Top of Search Results"
        HOMEPAGE_FEATURE = "homepage_feature", "Homepage Featured Job"
        EMAIL_BLAST = "email_blast", "Job Alert Email Blast"
        SOCIAL_BOOST = "social_boost", "Social Media Boost"
        BANNER_AD = "banner_ad", "Banner Ad Placement"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    promotion_type = models.CharField(max_length=20, choices=PromotionType.choices, unique=True)
    description = models.TextField(blank=True, default="")
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_days = models.IntegerField(help_text="Number of days the promotion runs")
    guaranteed_impressions = models.IntegerField(default=0, help_text="0 = no guarantee; > 0 = minimum impressions")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_promoted_job_products"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_lkr} ({self.duration_days}d)"


class PromotedJobOrder(models.Model):
    """Employer purchases a promotion slot for a specific job listing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="promoted_job_orders")
    job_listing_id = models.UUIDField(help_text="FK to jobs.JobListing — string ref to avoid circular import")
    product = models.ForeignKey(PromotedJobProduct, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    amount_paid_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    impressions_delivered = models.IntegerField(default=0)
    clicks_delivered = models.IntegerField(default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    # Source of payment: wallet deduction or direct payment
    paid_from_ad_budget = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_promoted_job_orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Promo {self.product.name} — {self.employer} ({self.status})"


class CpcCampaign(models.Model):
    """Cost-per-click campaign funded from employer AdBudget wallet."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="cpc_campaigns")
    ad_budget = models.ForeignKey("marketplace_billing.AdBudget", on_delete=models.PROTECT,
                                  related_name="cpc_campaigns")
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    max_cpc_lkr = models.DecimalField(max_digits=8, decimal_places=2,
                                      help_text="Maximum cost per click willing to pay")
    daily_budget_lkr = models.DecimalField(max_digits=10, decimal_places=2,
                                           help_text="Daily spend cap; 0 = no cap")
    total_budget_lkr = models.DecimalField(max_digits=12, decimal_places=2,
                                           help_text="Total campaign budget cap; 0 = no cap")
    total_spent_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    target_job_ids = models.JSONField(default=list, help_text="List of job listing UUIDs to include in campaign")
    targeting_criteria = models.JSONField(default=dict,
                                          help_text="Skills, location, experience level, category filters")
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_cpc_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"CPC Campaign: {self.name} — {self.employer} ({self.status})"

    @property
    def average_cpc_lkr(self):
        if self.clicks == 0:
            return 0
        return round(self.total_spent_lkr / self.clicks, 2)


class CpaCampaign(models.Model):
    """Cost-per-application campaign — employer pays per qualified application received."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="cpa_campaigns")
    ad_budget = models.ForeignKey("marketplace_billing.AdBudget", on_delete=models.PROTECT,
                                  related_name="cpa_campaigns")
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    cost_per_application_lkr = models.DecimalField(max_digits=8, decimal_places=2)
    total_budget_lkr = models.DecimalField(max_digits=12, decimal_places=2,
                                           help_text="Campaign total spend cap; 0 = no cap")
    total_spent_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    applications_received = models.IntegerField(default=0)
    qualified_applications = models.IntegerField(default=0,
                                                 help_text="Applications meeting employer-defined qualification criteria")
    qualification_criteria = models.JSONField(default=dict,
                                              help_text="Min experience, skills, education thresholds")
    target_job_ids = models.JSONField(default=list)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_cpa_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"CPA Campaign: {self.name} — {self.employer} ({self.status})"

    @property
    def cost_per_qualified_application_lkr(self):
        if self.qualified_applications == 0:
            return 0
        return round(self.total_spent_lkr / self.qualified_applications, 2)


class RecruiterMessagingPack(models.Model):
    """Bulk messaging credit packs — recruiters purchase credits to contact candidates directly."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    credits = models.IntegerField(help_text="Number of candidate messages included")
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    validity_days = models.IntegerField(default=90, help_text="Credits expire after this many days")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_recruiter_messaging_packs"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — {self.credits} messages — LKR {self.price_lkr}"


class RecruiterMessagingPurchase(models.Model):
    """Record of an employer purchasing a recruiter messaging pack."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="messaging_purchases")
    pack = models.ForeignKey(RecruiterMessagingPack, on_delete=models.PROTECT, related_name="purchases")
    credits_remaining = models.IntegerField()
    amount_paid_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_recruiter_messaging_purchases"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employer} — {self.pack.name} ({self.credits_remaining} remaining)"


class ApplicantScreeningAddon(models.Model):
    """AI-powered applicant screening add-on — purchasable per job post."""

    class ScreeningTier(models.TextChoices):
        BASIC = "basic", "Basic (keyword match + ranking)"
        ADVANCED = "advanced", "Advanced (AI scoring + shortlist)"
        FULL = "full", "Full (AI + video screening + report)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    screening_tier = models.CharField(max_length=10, choices=ScreeningTier.choices, unique=True)
    description = models.TextField(blank=True, default="")
    price_per_job_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_job_usd = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_applicants_screened = models.IntegerField(default=200,
                                                  help_text="-1 = unlimited; beyond this, extra charge applies")
    overage_per_applicant_lkr = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_applicant_screening_addons"

    def __str__(self):
        return f"{self.name} — LKR {self.price_per_job_lkr}/job"


class ApplicantScreeningOrder(models.Model):
    """Employer activates screening add-on for a specific job listing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="screening_orders")
    job_listing_id = models.UUIDField(help_text="FK to jobs.JobListing")
    addon = models.ForeignKey(ApplicantScreeningAddon, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    applicants_screened = models.IntegerField(default=0)
    base_amount_paid_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    overage_charged_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    screening_report = models.JSONField(default=dict, blank=True,
                                        help_text="Aggregate screening results and shortlist data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_applicant_screening_orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Screening [{self.addon.screening_tier}] — {self.employer} ({self.status})"

    @property
    def total_charged_lkr(self):
        return self.base_amount_paid_lkr + self.overage_charged_lkr


class ResponseRateAnalyticsPack(models.Model):
    """Advanced analytics packs — response rate benchmarks, funnel data, competitor insights."""

    class PackType(models.TextChoices):
        JOB_PERFORMANCE = "job_performance", "Job Performance Analytics"
        CANDIDATE_FUNNEL = "candidate_funnel", "Candidate Funnel Report"
        MARKET_BENCHMARK = "market_benchmark", "Market Salary & Hiring Benchmark"
        FULL_SUITE = "full_suite", "Full Analytics Suite"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    pack_type = models.CharField(max_length=20, choices=PackType.choices, unique=True)
    description = models.TextField(blank=True, default="")
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2,
                                    help_text="One-time or per-period access fee")
    validity_days = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_response_rate_analytics_packs"

    def __str__(self):
        return f"{self.name} — LKR {self.price_lkr}"


class ResponseRateAnalyticsPurchase(models.Model):
    """Employer purchases an analytics pack for a defined access period."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="analytics_purchases")
    pack = models.ForeignKey(ResponseRateAnalyticsPack, on_delete=models.PROTECT, related_name="purchases")
    amount_paid_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    access_from = models.DateTimeField()
    access_until = models.DateTimeField()
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    report_data = models.JSONField(default=dict, blank=True,
                                   help_text="Cached report snapshot at time of purchase")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_response_rate_analytics_purchases"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employer} — {self.pack.name}"


# ---------------------------------------------------------------------------
# Layer 3 — Commerce & Services
# ---------------------------------------------------------------------------

class SalaryReportSponsorship(models.Model):
    """Employer sponsors a salary-benchmark report page — brand placement on data content."""

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending Review"
        LIVE = "live", "Live"
        EXPIRED = "expired", "Expired"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="salary_report_sponsorships")
    # Identifies which salary report page / category is being sponsored
    report_category = models.CharField(max_length=200,
                                       help_text="e.g. 'Software Engineering Sri Lanka 2025'")
    report_slug = models.SlugField(max_length=200,
                                   help_text="URL-safe identifier matching the report page slug")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    sponsorship_fee_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    logo_url = models.URLField(blank=True, default="")
    cta_text = models.CharField(max_length=100, blank=True, default="")
    cta_url = models.URLField(blank=True, default="")
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_bm_salary_report_sponsorships"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sponsorship: {self.report_category} — {self.employer} ({self.status})"


class ResumeDbAccessRecord(models.Model):
    """Per-view or per-download charge record for resume database access (pay-as-you-go)."""

    class AccessType(models.TextChoices):
        VIEW = "view", "CV View"
        DOWNLOAD = "download", "CV Download"
        CONTACT_REVEAL = "contact_reveal", "Contact Details Reveal"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="resume_db_access_records")
    # Source of entitlement: subscription quota or pay-as-you-go
    resume_db_subscription = models.ForeignKey(ResumeDatabaseSubscription, on_delete=models.SET_NULL,
                                               null=True, blank=True, related_name="access_records",
                                               help_text="Null = pay-as-you-go access")
    candidate_profile_id = models.UUIDField(help_text="FK to candidate profile — string ref to avoid circular import")
    access_type = models.CharField(max_length=15, choices=AccessType.choices)
    charged_lkr = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                      help_text="0 if covered by subscription quota; >0 for PAYG or overage")
    is_subscription_quota = models.BooleanField(default=True,
                                                help_text="True = deducted from subscription quota")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_resume_db_access_records"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employer", "candidate_profile_id"]),
        ]

    def __str__(self):
        return f"{self.access_type} — {self.employer} — LKR {self.charged_lkr}"


# ---------------------------------------------------------------------------
# Audit — Billing Event Log
# ---------------------------------------------------------------------------

class JobFinderBillingEvent(models.Model):
    """Append-only audit log for all billing-related events across Job Finder revenue streams."""

    class EventType(models.TextChoices):
        SUBSCRIPTION_CREATED = "subscription_created", "Subscription Created"
        SUBSCRIPTION_RENEWED = "subscription_renewed", "Subscription Renewed"
        SUBSCRIPTION_CANCELLED = "subscription_cancelled", "Subscription Cancelled"
        SUBSCRIPTION_EXPIRED = "subscription_expired", "Subscription Expired"
        CREDITS_PURCHASED = "credits_purchased", "Credits Purchased"
        CREDITS_CONSUMED = "credits_consumed", "Credits Consumed"
        CREDITS_EXPIRED = "credits_expired", "Credits Expired"
        PROMOTION_PURCHASED = "promotion_purchased", "Promotion Purchased"
        CAMPAIGN_STARTED = "campaign_started", "Campaign Started"
        CAMPAIGN_PAUSED = "campaign_paused", "Campaign Paused"
        CAMPAIGN_COMPLETED = "campaign_completed", "Campaign Completed"
        AD_SPEND_DEDUCTED = "ad_spend_deducted", "Ad Spend Deducted from Wallet"
        WALLET_TOPPED_UP = "wallet_topped_up", "Ad Wallet Topped Up"
        INVOICE_PAID = "invoice_paid", "Invoice Paid"
        REFUND_ISSUED = "refund_issued", "Refund Issued"
        SCREENING_ACTIVATED = "screening_activated", "Screening Add-on Activated"
        RESUME_ACCESSED = "resume_accessed", "Resume Database Accessed"
        SPONSORSHIP_LIVE = "sponsorship_live", "Salary Report Sponsorship Live"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="jf_billing_events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    amount_lkr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # Generic reference to any related billing object
    object_type = models.CharField(max_length=100, blank=True, default="",
                                   help_text="Model name of the related billing object")
    object_id = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    meta = models.JSONField(default=dict, blank=True, help_text="Additional context for the event")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bm_billing_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.event_type}] {self.employer} — LKR {self.amount_lkr}"
