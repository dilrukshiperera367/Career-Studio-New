"""
TalentOS Business Model — Seat-based SaaS + Usage-based Recruiting Revenue.

Revenue streams covered:
    Layer 1 — Recurring software revenue:
        - Recruiter seats (Starter / Growth / Enterprise plans)
        - Hiring manager seat add-ons
        - Annual vs monthly billing (15–20% annual discount)

    Layer 2 — Transactional / usage revenue:
        - Job posting credits (beyond plan limit)
        - Promoted / featured job boosts
        - SMS / WhatsApp / email communication credits
        - Candidate verification purchases
        - Assessment integration purchases
        - Employer branding add-on (career site CMS, banner ads)
        - Sourcing / recruiter messaging credits
        - Premium analytics / AI copilot add-ons
        - API / webhook volume overages
        - Recruiter seat overages (beyond plan seat count)

    Layer 3 — Commerce / services revenue:
        - ATS implementation services
        - Data migration services
        - Premium support SLAs
        - Recruiter / HR training sessions
        - Custom workflow / integration consulting
        - Featured employer campaign packages

Pricing bands (LKR-first):
    Starter   — LKR 7,500–25,000/month  (SMBs, 1–5 recruiters)
    Growth    — LKR 30,000–100,000/month (growing teams)
    Enterprise — custom / invoiced
"""

import uuid
from django.db import models


# ---------------------------------------------------------------------------
# Plan Definitions
# ---------------------------------------------------------------------------

class TalentPlan(models.Model):
    """
    TalentOS subscription plan definition (seat-based SaaS).
    One plan record exists per tier; subscriptions reference a plan.
    """

    class Tier(models.TextChoices):
        STARTER = "starter", "Starter"
        GROWTH = "growth", "Growth"
        ENTERPRISE = "enterprise", "Enterprise"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    # LKR-first pricing
    price_monthly_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Base monthly platform fee in LKR (before per-seat charges).",
    )
    price_annual_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Annual price in LKR. Typically 15–20% discount vs monthly × 12.",
    )
    price_per_recruiter_seat_monthly_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Per recruiter seat charge per month (on top of base fee).",
    )

    # Stripe Price IDs
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, default="")
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")

    # Included seats
    included_recruiter_seats = models.IntegerField(
        default=1, help_text="Recruiter seats included in base price.",
    )
    included_hiring_manager_seats = models.IntegerField(
        default=3, help_text="Hiring manager light-access seats included.",
    )

    # Plan limits
    job_posting_limit = models.IntegerField(
        default=5, help_text="Active job postings allowed. -1 = unlimited.",
    )
    candidate_limit = models.IntegerField(
        default=500, help_text="Candidate profiles in system. -1 = unlimited.",
    )
    workflow_limit = models.IntegerField(
        default=3, help_text="Active automation workflows. -1 = unlimited.",
    )
    storage_gb = models.IntegerField(
        default=5, help_text="Document/resume storage in GB. -1 = unlimited.",
    )
    api_access = models.BooleanField(default=False)
    advanced_analytics = models.BooleanField(default=False)
    employer_branding = models.BooleanField(default=False)
    ai_copilot = models.BooleanField(default=False)
    compliance_ai = models.BooleanField(default=False)
    sso_scim = models.BooleanField(default=False)
    white_label_career_site = models.BooleanField(default=False)
    dedicated_support = models.BooleanField(default=False)
    custom_sla = models.BooleanField(default=False)

    # Trial
    trial_days = models.IntegerField(default=14)

    features = models.JSONField(default=list, help_text="Marketing bullet points.")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "talent_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_monthly_lkr}/mo"


# ---------------------------------------------------------------------------
# Tenant Subscription (plan + seat tracking)
# ---------------------------------------------------------------------------

class TalentSubscription(models.Model):
    """
    Active or historical subscription for a TalentOS tenant.
    Seat-based: base price + per-seat overage.
    """

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        SUSPENDED = "suspended", "Suspended"
        EXPIRED = "expired", "Expired"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    class Gateway(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        PAYHERE = "payhere", "PayHere"
        INVOICE = "invoice", "Invoice / Bank Transfer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="talent_subscription",
    )
    plan = models.ForeignKey(
        TalentPlan, on_delete=models.PROTECT, related_name="subscriptions",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.TRIAL)
    billing_cycle = models.CharField(
        max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY,
    )
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.STRIPE)

    # Current seat counts
    recruiter_seats_purchased = models.IntegerField(default=1)
    recruiter_seats_used = models.IntegerField(default=0)
    hiring_manager_seats_purchased = models.IntegerField(default=3)
    hiring_manager_seats_used = models.IntegerField(default=0)

    # Billing period
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Gateway references
    stripe_customer_id = models.CharField(max_length=100, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default="")
    payhere_subscription_id = models.CharField(max_length=100, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "talent_subscriptions"

    def __str__(self):
        return f"{self.tenant} — {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        return self.status in (self.Status.ACTIVE, self.Status.TRIAL)

    @property
    def recruiter_seat_overage(self):
        return max(0, self.recruiter_seats_used - self.recruiter_seats_purchased)


# ---------------------------------------------------------------------------
# Plan Add-ons (module-level optional upgrades)
# ---------------------------------------------------------------------------

class TalentAddon(models.Model):
    """
    Optional paid add-ons that can be purchased on top of any plan.
    Add-ons unlock specific platform modules or higher usage limits.
    """

    class AddonType(models.TextChoices):
        ADVANCED_ANALYTICS = "advanced_analytics", "Advanced Analytics & Reporting"
        EMPLOYER_BRANDING = "employer_branding", "Employer Branding & Career Site CMS"
        AI_COPILOT = "ai_copilot", "AI Hiring Copilot"
        COMPLIANCE_AI = "compliance_ai", "Compliance AI & Bias Review"
        STRUCTURED_INTERVIEWS = "structured_interviews", "Structured Interview Templates"
        ASSESSMENT_INTEGRATION = "assessment_integration", "Assessment Platform Integration"
        SSO_SCIM = "sso_scim", "SSO / SCIM Enterprise Identity"
        DATA_MIGRATION = "data_migration", "Data Migration Service (one-off)"
        PREMIUM_SUPPORT = "premium_support", "Premium Support SLA"
        CUSTOM_WORKFLOWS = "custom_workflows", "Custom Automation Workflows"
        CANDIDATE_VERIFICATION = "candidate_verification", "Candidate Verification Credits"
        SOURCING_INTEGRATION = "sourcing_integration", "Premium Sourcing Integration"
        WHITE_LABEL_CAREER_SITE = "white_label_career_site", "White-Label Career Site"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    addon_type = models.CharField(max_length=40, choices=AddonType.choices, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    price_monthly_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_annual_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_one_off = models.BooleanField(
        default=False,
        help_text="If True, this is a one-time purchase (e.g. data migration), not recurring.",
    )
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, default="")
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")
    compatible_tiers = models.JSONField(
        default=list,
        help_text="List of TalentPlan tiers this add-on is available for.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talent_addons"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_monthly_lkr}/mo"


class TenantAddonSubscription(models.Model):
    """Tracks which add-ons a tenant has activated."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"
        PENDING = "pending", "Pending Activation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="addon_subscriptions",
    )
    addon = models.ForeignKey(
        TalentAddon, on_delete=models.PROTECT, related_name="tenant_subscriptions",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    billing_cycle = models.CharField(
        max_length=10,
        choices=[("monthly", "Monthly"), ("annual", "Annual")],
        default="monthly",
    )
    activated_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    stripe_subscription_item_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "talent_tenant_addon_subscriptions"
        unique_together = [("tenant", "addon")]

    def __str__(self):
        return f"{self.tenant} + {self.addon.name} ({self.status})"


# ---------------------------------------------------------------------------
# Job Posting Credits & Promotions (transactional)
# ---------------------------------------------------------------------------

class JobPostingCreditPack(models.Model):
    """
    Pre-purchased job posting credit packs (beyond plan-included quota).
    Used to post, renew, or boost job listings on the Job Finder marketplace.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    posting_credits = models.IntegerField(help_text="Number of job post credits.")
    validity_days = models.IntegerField(
        default=365, help_text="Credits expire after this many days from purchase.",
    )
    price_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talent_job_posting_credit_packs"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name}: {self.posting_credits} credits — LKR {self.price_lkr}"


class JobPromotionProduct(models.Model):
    """
    One-off promoted / featured job upgrades purchasable per-listing.
    Applied on a per-job basis after initial posting.
    """

    class PromotionType(models.TextChoices):
        FEATURED_JOB = "featured_job", "Featured Job (top of search results)"
        URGENT_BADGE = "urgent_badge", "Urgent Hiring Badge"
        SPOTLIGHT_EMAIL = "spotlight_email", "Spotlight Email Blast to Candidates"
        SOCIAL_BOOST = "social_boost", "Social Media Boost"
        CATEGORY_SPONSOR = "category_sponsor", "Category / City Landing Page Sponsor"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion_type = models.CharField(max_length=30, choices=PromotionType.choices)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=300, blank=True, default="")
    duration_days = models.IntegerField(help_text="How long the promotion lasts.")
    price_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talent_job_promotion_products"
        ordering = ["promotion_type", "sort_order"]

    def __str__(self):
        return f"{self.name} ({self.duration_days}d) — LKR {self.price_lkr}"


# ---------------------------------------------------------------------------
# Communication Credits (SMS / WhatsApp / Email overages)
# ---------------------------------------------------------------------------

class CommsCreditPack(models.Model):
    """
    Top-up packs for SMS, WhatsApp, and email message overages.
    Plans include a monthly quota; these packs extend beyond that quota.
    """

    class Channel(models.TextChoices):
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=15, choices=Channel.choices)
    name = models.CharField(max_length=150)
    message_count = models.IntegerField(help_text="Number of messages in this pack.")
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talent_comms_credit_packs"
        ordering = ["channel", "sort_order"]

    def __str__(self):
        return f"{self.channel.upper()} {self.message_count} msgs — LKR {self.price_lkr}"


# ---------------------------------------------------------------------------
# Employer Branding Packages (one-off / recurring campaign products)
# ---------------------------------------------------------------------------

class EmployerBrandingPackage(models.Model):
    """
    Employer branding and recruitment marketing packages.
    Sold as add-ons or standalone campaigns to employers using TalentOS or Job Finder.
    """

    class PackageType(models.TextChoices):
        CAREER_SITE_SETUP = "career_site_setup", "Career Site Setup & Launch (one-off service)"
        FEATURED_EMPLOYER = "featured_employer", "Featured Employer Profile"
        EMPLOYER_STORY = "employer_story", "Sponsored Employer Story / Content"
        HIRING_CAMPAIGN = "hiring_campaign", "Targeted Hiring Campaign Page"
        CAMPUS_CAMPAIGN = "campus_campaign", "Campus Employer Branding Campaign"
        SALARY_REPORT_SPONSORSHIP = "salary_report_sponsorship", "Salary Report Sponsorship"
        WEBINAR_SPONSORSHIP = "webinar_sponsorship", "Promoted Webinar / Hiring Event"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_type = models.CharField(max_length=35, choices=PackageType.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    deliverables = models.JSONField(default=list)
    duration_days = models.IntegerField(
        null=True, blank=True, help_text="For time-limited campaigns.",
    )
    is_one_off = models.BooleanField(default=True)
    price_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talent_employer_branding_packages"
        ordering = ["package_type", "sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_lkr}"


class EmployerBrandingOrder(models.Model):
    """Records an employer's purchase of a branding package."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        PAID = "paid", "Paid"
        IN_PROGRESS = "in_progress", "In Progress"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="branding_orders",
    )
    package = models.ForeignKey(
        EmployerBrandingPackage, on_delete=models.PROTECT, related_name="orders",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    amount_paid_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    brief = models.JSONField(default=dict, help_text="Campaign brief / requirements.")
    deliverables_submitted = models.JSONField(default=list)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "talent_employer_branding_orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant} — {self.package.name} ({self.status})"


# ---------------------------------------------------------------------------
# Implementation & Professional Services (Layer 3)
# ---------------------------------------------------------------------------

class ProfessionalServiceProduct(models.Model):
    """
    One-off professional services: implementation, training, consulting.
    Invoiced separately from subscription; fulfillment tracked per order.
    """

    class ServiceType(models.TextChoices):
        IMPLEMENTATION = "implementation", "ATS Implementation & Onboarding"
        DATA_MIGRATION = "data_migration", "Data Migration"
        RECRUITER_TRAINING = "recruiter_training", "Recruiter / HR Admin Training"
        CUSTOM_INTEGRATION = "custom_integration", "Custom Integration Consulting"
        WORKFLOW_CONSULTING = "workflow_consulting", "Workflow & Process Consulting"
        SUPPORT_SLA = "support_sla", "Premium Support SLA (annual)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    scope = models.JSONField(default=list, help_text="Scope of work bullet points.")
    estimated_hours = models.IntegerField(null=True, blank=True)
    price_lkr = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Fixed price. 0 = quoted on request.",
    )
    is_quoted = models.BooleanField(
        default=False, help_text="If True, price is determined per quote.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talent_professional_service_products"
        ordering = ["service_type", "sort_order"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Billing Invoice & History
# ---------------------------------------------------------------------------

class TalentInvoice(models.Model):
    """Invoice record for all TalentOS charges."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"
        REFUNDED = "refunded", "Refunded"

    class LineItemType(models.TextChoices):
        SUBSCRIPTION = "subscription", "Subscription"
        SEAT_OVERAGE = "seat_overage", "Seat Overage"
        ADDON = "addon", "Plan Add-on"
        JOB_CREDITS = "job_credits", "Job Posting Credits"
        PROMOTION = "promotion", "Job Promotion"
        COMMS_CREDITS = "comms_credits", "Comms Credits"
        BRANDING = "branding", "Employer Branding"
        SERVICES = "services", "Professional Services"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="talent_invoices",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    line_items = models.JSONField(default=list)
    subtotal_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    discount_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    payment_gateway = models.CharField(max_length=30, blank=True, default="")
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    stripe_invoice_id = models.CharField(max_length=100, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "talent_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.tenant} — LKR {self.total_lkr}"


class TalentBillingEvent(models.Model):
    """Immutable audit log of all TalentOS billing lifecycle events."""

    class EventType(models.TextChoices):
        TRIAL_STARTED = "trial_started", "Trial Started"
        TRIAL_EXPIRED = "trial_expired", "Trial Expired"
        SUBSCRIPTION_CREATED = "subscription_created", "Subscription Created"
        PLAN_UPGRADED = "plan_upgraded", "Plan Upgraded"
        PLAN_DOWNGRADED = "plan_downgraded", "Plan Downgraded"
        ADDON_ACTIVATED = "addon_activated", "Add-on Activated"
        ADDON_CANCELLED = "addon_cancelled", "Add-on Cancelled"
        SEAT_ADDED = "seat_added", "Seat Added"
        SEAT_REMOVED = "seat_removed", "Seat Removed"
        PAYMENT_SUCCEEDED = "payment_succeeded", "Payment Succeeded"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        SUBSCRIPTION_CANCELLED = "subscription_cancelled", "Subscription Cancelled"
        REFUND_ISSUED = "refund_issued", "Refund Issued"
        INVOICE_GENERATED = "invoice_generated", "Invoice Generated"
        CREDITS_PURCHASED = "credits_purchased", "Credits Purchased"
        BRANDING_ORDER_PLACED = "branding_order_placed", "Branding Order Placed"
        SERVICE_ORDER_PLACED = "service_order_placed", "Service Order Placed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="talent_billing_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    amount_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    plan_before = models.CharField(max_length=30, blank=True, default="")
    plan_after = models.CharField(max_length=30, blank=True, default="")
    seats_before = models.IntegerField(null=True, blank=True)
    seats_after = models.IntegerField(null=True, blank=True)
    gateway_event_id = models.CharField(max_length=200, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talent_billing_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant} — {self.event_type} ({self.created_at:%Y-%m-%d})"
