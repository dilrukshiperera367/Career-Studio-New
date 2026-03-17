"""
MarketplaceOS Business Model — Take rate + provider subscriptions + featured listings
+ enterprise private marketplace.

Revenue streams covered:
    Layer 1 — Recurring provider subscriptions:
        - ProviderPlan: subscription tiers for coaches, mentors, consultants
        - ProviderSubscription: provider's active subscription

    Layer 2 — Transactional (take rate / commission model):
        - MarketplaceCommissionConfig: category-level take rate configuration
          (10–25% depending on category)
        - BookingCommission: per-session booking commission record
        - CourseCommission: per-course-sale commission record
        - VerificationFee: provider profile verification / badge purchase
        - FeaturedListingProduct: featured expert slot products
        - FeaturedListingPurchase: provider purchase of featured slots

    Layer 3 — Enterprise / commerce revenue:
        - EnterpriseBudget: employer-sponsored coaching / session budgets
        - EnterpriseBudgetTransaction: deposit / spend / refund ledger
        - EnterpriseMpSetup: one-off private marketplace setup fee
        - MarketplaceServiceProduct: marketplace consulting services
        - CoachingBundle: pre-packaged session bundles (B2C upsell)

Pricing model:
    Take rate: 10–25% per booked session or course sale
    Provider subscription: visibility tier (Basic free / Pro paid / Featured)
    Enterprise budget: employer pre-loads a coaching credit wallet
    Featured listings: monthly flat fee per featured slot
"""

import uuid
from django.db import models
from django.conf import settings


# ---------------------------------------------------------------------------
# Provider Plan (subscription tier for coaches / mentors / consultants)
# ---------------------------------------------------------------------------

class ProviderPlan(models.Model):
    """
    Subscription plan for service providers (coaches, mentors, consultants,
    assessors, trainers) listed on MarketplaceOS.
    """

    class Tier(models.TextChoices):
        BASIC = "basic", "Basic (Free — limited visibility)"
        PRO = "pro", "Pro (Paid — enhanced visibility + analytics)"
        FEATURED = "featured", "Featured (Premium — top placement + verification badge)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=15, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    price_monthly_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_annual_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, default="")
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")
    payhere_plan_id = models.CharField(max_length=100, blank=True, default="")

    # Visibility & feature limits
    profile_listing_slots = models.IntegerField(
        default=1, help_text="Number of service listing slots. -1 = unlimited.",
    )
    course_listing_slots = models.IntegerField(default=0)
    featured_in_search = models.BooleanField(default=False)
    analytics_dashboard = models.BooleanField(default=False)
    review_response = models.BooleanField(default=False)
    booking_calendar_integration = models.BooleanField(default=False)
    instant_booking = models.BooleanField(default=False)
    bulk_booking = models.BooleanField(default=False)
    enterprise_bookings = models.BooleanField(
        default=False, help_text="Eligible for employer-sponsored budget bookings.",
    )

    # Commission rate override for this tier (overrides category default)
    commission_rate_override_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="If set, overrides the category take rate for this provider tier.",
    )

    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_provider_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_monthly_lkr}/mo"


class ProviderSubscription(models.Model):
    """A provider's active MarketplaceOS subscription."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRIALING = "trialing", "Trialing"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "marketplace.Provider", on_delete=models.CASCADE, related_name="subscriptions",
    )
    plan = models.ForeignKey(
        ProviderPlan, on_delete=models.PROTECT, related_name="subscriptions",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    billing_cycle = models.CharField(
        max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=100, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default="")
    payhere_subscription_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_provider_subscriptions"

    def __str__(self):
        return f"{self.provider} — {self.plan.name} ({self.status})"


# ---------------------------------------------------------------------------
# Commission Configuration (take rate engine)
# ---------------------------------------------------------------------------

class MarketplaceCommissionConfig(models.Model):
    """
    Take rate configuration per service category.
    Default range: 10–25% depending on category value and volume.
    """

    class Category(models.TextChoices):
        CAREER_COACHING = "career_coaching", "Career Coaching"
        INTERVIEW_COACHING = "interview_coaching", "Interview Coaching"
        RESUME_SERVICES = "resume_services", "Resume & CV Services"
        MENTORSHIP = "mentorship", "Mentorship"
        LEADERSHIP_COACHING = "leadership_coaching", "Leadership & Executive Coaching"
        HR_CONSULTING = "hr_consulting", "HR & People Consulting"
        LEARNING_COURSES = "learning_courses", "Learning Courses"
        ASSESSMENTS = "assessments", "Assessment & Testing Services"
        RECRUITMENT_TRAINING = "recruitment_training", "Recruiter Training"
        OUTPLACEMENT = "outplacement", "Outplacement Services"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=30, choices=Category.choices, unique=True)
    commission_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Platform take rate percentage on each completed transaction.",
    )
    min_commission_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Minimum commission per transaction in LKR (floor amount).",
    )
    max_commission_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Optional maximum commission cap in LKR.",
    )
    notes = models.CharField(max_length=300, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_commission_configs"

    def __str__(self):
        return f"{self.get_category_display()} — {self.commission_rate_pct}% take rate"

    def calculate_commission(self, transaction_amount_lkr: "Decimal") -> "Decimal":
        from decimal import Decimal
        commission = transaction_amount_lkr * (
            Decimal(str(self.commission_rate_pct)) / Decimal("100")
        )
        commission = max(commission, Decimal(str(self.min_commission_lkr)))
        if self.max_commission_lkr:
            commission = min(commission, Decimal(str(self.max_commission_lkr)))
        return commission.quantize(Decimal("0.01"))


class BookingCommission(models.Model):
    """
    Commission record for each completed session booking.
    Immutable ledger entry created on booking completion.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending (booking not completed)"
        EARNED = "earned", "Earned (booking completed)"
        HELD = "held", "Held (dispute / guarantee window)"
        RELEASED = "released", "Released to Provider"
        REFUNDED = "refunded", "Refunded to Client"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "marketplace.Provider", on_delete=models.CASCADE, related_name="booking_commissions",
    )
    booking_reference = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=MarketplaceCommissionConfig.Category.choices)
    session_title = models.CharField(max_length=200)
    booking_date = models.DateField()
    session_date = models.DateField(null=True, blank=True)
    client_user_id = models.CharField(max_length=100, blank=True, default="")

    gross_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate_pct = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    net_to_provider_lkr = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    payout_date = models.DateField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_booking_commissions"
        ordering = ["-booking_date"]

    def __str__(self):
        return (
            f"{self.provider} — {self.session_title} "
            f"LKR {self.commission_amount_lkr} commission ({self.status})"
        )


class CourseCommission(models.Model):
    """Commission record for each course sale through MarketplaceOS."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        EARNED = "earned", "Earned"
        REFUNDED = "refunded", "Refunded"
        RELEASED = "released", "Released to Provider"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "marketplace.Provider", on_delete=models.CASCADE, related_name="course_commissions",
    )
    course_reference = models.CharField(max_length=200)
    course_title = models.CharField(max_length=200)
    sale_date = models.DateField()
    buyer_user_id = models.CharField(max_length=100, blank=True, default="")
    gross_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate_pct = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    net_to_provider_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    payout_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_course_commissions"
        ordering = ["-sale_date"]

    def __str__(self):
        return f"{self.provider} — {self.course_title} — LKR {self.commission_amount_lkr}"


# ---------------------------------------------------------------------------
# Featured Listing Products (pay-for-visibility)
# ---------------------------------------------------------------------------

class FeaturedListingProduct(models.Model):
    """
    Featured expert slot products providers can purchase.
    Provides premium placement in search results, category pages, or homepage.
    """

    class SlotType(models.TextChoices):
        SEARCH_TOP = "search_top", "Top of Search Results"
        CATEGORY_FEATURED = "category_featured", "Category Page Featured Expert"
        HOMEPAGE_SPOTLIGHT = "homepage_spotlight", "Homepage Spotlight"
        NEWSLETTER_FEATURE = "newsletter_feature", "Newsletter Feature"
        CAREEROS_SIDEBAR = "careeros_sidebar", "CareerOS Sidebar Recommendation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot_type = models.CharField(max_length=25, choices=SlotType.choices)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=300, blank=True, default="")
    duration_days = models.IntegerField(help_text="Duration of the featured placement.")
    max_concurrent_slots = models.IntegerField(
        default=5, help_text="Max providers featured simultaneously in this slot.",
    )
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_featured_listing_products"
        ordering = ["slot_type", "sort_order"]

    def __str__(self):
        return f"{self.name} ({self.duration_days}d) — LKR {self.price_lkr}"


class FeaturedListingPurchase(models.Model):
    """Records a provider's purchase of a featured listing slot."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "marketplace.Provider", on_delete=models.CASCADE, related_name="featured_purchases",
    )
    listing_product = models.ForeignKey(
        FeaturedListingProduct, on_delete=models.PROTECT, related_name="purchases",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    amount_paid_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_featured_listing_purchases"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} — {self.listing_product.name} ({self.status})"


# ---------------------------------------------------------------------------
# Provider Verification Fee
# ---------------------------------------------------------------------------

class ProviderVerificationProduct(models.Model):
    """
    Paid provider verification badge — credential check and identity verification.
    One-off purchase; badge displayed on provider profile.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    verification_scope = models.JSONField(
        default=list,
        help_text="What is verified: ['identity', 'credentials', 'background_check'].",
    )
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    badge_validity_months = models.IntegerField(
        default=12, help_text="Months the verification badge remains valid.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_verification_products"

    def __str__(self):
        return f"{self.name} — LKR {self.price_lkr}"


# ---------------------------------------------------------------------------
# Enterprise Coaching Budget (employer-sponsored coaching wallet)
# ---------------------------------------------------------------------------

class EnterpriseBudget(models.Model):
    """
    An employer's pre-loaded coaching / mentorship session budget.
    Employees redeem sessions from the employer's wallet balance.
    Works like the Job Finder AdBudget — deposit → spend → refund ledger.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer_reference = models.CharField(
        max_length=200,
        help_text="Cross-reference to TalentOS or WorkforceOS tenant ID.",
    )
    employer_name = models.CharField(max_length=300)
    balance_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deposited_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_spent_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    auto_topup_enabled = models.BooleanField(default=False)
    auto_topup_threshold_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    auto_topup_amount_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    max_spend_per_employee_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Per-employee monthly or annual spend cap.",
    )
    allowed_categories = models.JSONField(
        default=list,
        help_text="List of MarketplaceCommissionConfig category values allowed. Empty = all.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_enterprise_budgets"

    def __str__(self):
        return f"Enterprise Budget: {self.employer_name} — LKR {self.balance_lkr}"


class EnterpriseBudgetTransaction(models.Model):
    """Ledger of every enterprise budget change."""

    class TxType(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        SPEND = "spend", "Session/Course Spend"
        REFUND = "refund", "Refund"
        CREDIT = "credit", "Promotional Credit"
        EXPIRY = "expiry", "Balance Expiry"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(
        EnterpriseBudget, on_delete=models.CASCADE, related_name="transactions",
    )
    tx_type = models.CharField(max_length=10, choices=TxType.choices)
    amount_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    employee_reference = models.CharField(max_length=200, blank=True, default="")
    booking_reference = models.CharField(max_length=200, blank=True, default="")
    description = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_enterprise_budget_transactions"
        ordering = ["-created_at"]


# ---------------------------------------------------------------------------
# Private Marketplace Setup (one-off enterprise service)
# ---------------------------------------------------------------------------

class EnterpriseMpSetup(models.Model):
    """
    One-off setup fee for an enterprise's private branded marketplace instance.
    Delivered as a professional service.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        PAID = "paid", "Paid"
        SETUP_IN_PROGRESS = "setup_in_progress", "Setup In Progress"
        LIVE = "live", "Live"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer_reference = models.CharField(max_length=200)
    employer_name = models.CharField(max_length=300)
    setup_fee_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    monthly_license_fee_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Recurring monthly fee for maintaining the private marketplace.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount_paid_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    go_live_date = models.DateField(null=True, blank=True)
    branding_config = models.JSONField(default=dict)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_enterprise_setups"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Enterprise MP: {self.employer_name} ({self.status})"


# ---------------------------------------------------------------------------
# Invoice & Billing Events
# ---------------------------------------------------------------------------

class MarketplaceInvoice(models.Model):
    """Invoice for MarketplaceOS subscription / feature charges (provider-facing)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PAID = "paid", "Paid"
        UNPAID = "unpaid", "Unpaid"
        VOID = "void", "Void"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "marketplace.Provider", on_delete=models.CASCADE, related_name="invoices",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    line_items = models.JSONField(default=list)
    subtotal_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    tax_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_digits=10, choices=Status.choices, default=Status.UNPAID)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    stripe_invoice_id = models.CharField(max_length=100, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.provider} — LKR {self.total_lkr}"


class MarketplaceBillingEvent(models.Model):
    """Immutable audit log of MarketplaceOS billing events."""

    class EventType(models.TextChoices):
        SUBSCRIPTION_STARTED = "subscription_started", "Subscription Started"
        PLAN_UPGRADED = "plan_upgraded", "Plan Upgraded"
        COMMISSION_EARNED = "commission_earned", "Commission Earned"
        COMMISSION_RELEASED = "commission_released", "Commission Released to Provider"
        REFUND_ISSUED = "refund_issued", "Refund Issued"
        FEATURED_SLOT_PURCHASED = "featured_slot_purchased", "Featured Slot Purchased"
        VERIFICATION_PURCHASED = "verification_purchased", "Verification Badge Purchased"
        ENTERPRISE_DEPOSIT = "enterprise_deposit", "Enterprise Budget Deposited"
        ENTERPRISE_SETUP_PAID = "enterprise_setup_paid", "Enterprise Marketplace Setup Paid"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        SUBSCRIPTION_CANCELLED = "subscription_cancelled", "Subscription Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "marketplace.Provider", on_delete=models.CASCADE,
        related_name="billing_events", null=True, blank=True,
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    amount_lkr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gateway_event_id = models.CharField(max_length=200, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_billing_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} — {self.event_type} ({self.created_at:%Y-%m-%d})"
