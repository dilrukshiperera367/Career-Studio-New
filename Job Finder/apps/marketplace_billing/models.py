"""Marketplace Billing — plan management, subscriptions, invoices, ad wallet, campaigns, coupons."""
import uuid
from django.db import models
from django.conf import settings


class BillingPlan(models.Model):
    """Available subscription plans."""
    class Tier(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        PROFESSIONAL = "professional", "Professional"
        ENTERPRISE = "enterprise", "Enterprise"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=100)
    price_monthly_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_annual_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    job_posting_limit = models.IntegerField(default=3, help_text="-1 = unlimited")
    featured_job_slots = models.IntegerField(default=0)
    resume_database_access = models.BooleanField(default=False)
    analytics_level = models.CharField(max_length=10,
                                       choices=[("basic", "Basic"), ("advanced", "Advanced"), ("enterprise", "Enterprise")],
                                       default="basic")
    max_team_members = models.IntegerField(default=1)
    priority_support = models.BooleanField(default=False)
    custom_branding = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)
    features_json = models.JSONField(default=list, help_text="Marketing feature bullets")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_billing_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_monthly_lkr}/mo"


class EmployerSubscription(models.Model):
    """An employer's active or historical subscription."""
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        TRIAL = "trial", "Trial"
        PAST_DUE = "past_due", "Past Due"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="mb_subscriptions")
    plan = models.ForeignKey(BillingPlan, on_delete=models.PROTECT, related_name="mb_subscriptions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    billing_cycle = models.CharField(max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_employer_subscriptions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.employer} — {self.plan} ({self.status})"


class Invoice(models.Model):
    """Billing invoice record."""
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PAID = "paid", "Paid"
        UNPAID = "unpaid", "Unpaid"
        VOID = "void", "Void"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="mb_invoices")
    subscription = models.ForeignKey(EmployerSubscription, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="mb_invoices")
    invoice_number = models.CharField(max_length=50, unique=True)
    amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    description = models.TextField(blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    line_items = models.JSONField(default=list)
    payment_method = models.CharField(max_length=50, blank=True, default="")
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_mb_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — LKR {self.total_lkr} ({self.status})"


class AdBudget(models.Model):
    """Employer ad wallet with deposit and spend tracking."""
    employer = models.OneToOneField("employers.EmployerAccount", on_delete=models.CASCADE, related_name="ad_budget")
    balance_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deposited_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_spent_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    auto_topup_enabled = models.BooleanField(default=False)
    auto_topup_threshold_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    auto_topup_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_ad_budgets"

    def __str__(self):
        return f"AdBudget: {self.employer} — LKR {self.balance_lkr}"


class AdBudgetTransaction(models.Model):
    """Individual ad wallet deposit or spend transaction."""
    class TxType(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        SPEND = "spend", "Ad Spend"
        REFUND = "refund", "Refund"
        CREDIT = "credit", "Promo Credit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(AdBudget, on_delete=models.CASCADE, related_name="transactions")
    tx_type = models.CharField(max_length=10, choices=TxType.choices)
    amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=300, blank=True, default="")
    reference = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_ad_budget_transactions"
        ordering = ["-created_at"]


class CouponCode(models.Model):
    """Discount or credit coupon."""
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage Off"
        FIXED_LKR = "fixed_lkr", "Fixed Amount Off (LKR)"
        AD_CREDIT = "ad_credit", "Ad Credit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=15, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    plan = models.ForeignKey(BillingPlan, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="If set, only valid for this plan")
    max_uses = models.IntegerField(null=True, blank=True)
    uses_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_coupon_codes"

    def __str__(self):
        return f"Coupon {self.code}: {self.discount_type} {self.discount_value}"
