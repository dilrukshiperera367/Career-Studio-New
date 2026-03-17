"""
AgencyOS Business Model — Hybrid seat + desk license + commercial workflow fees.

Revenue streams covered:
    Layer 1 — Recurring software revenue:
        - AgencyPlan: recruiter seat + account manager seat tiers
        - AgencySubscription: agency-level subscription (Starter / Growth / Enterprise)
        - DeskLicenseAddon: additional desk / recruiter license add-ons

    Layer 2 — Transactional / usage revenue:
        - JobOrderCreditPack: credits for active job orders beyond plan limit
        - SubmissionCreditPack: candidate submittal credits
        - ContractorOpsFee: per-contractor / per-timesheet operational charges
        - PlacementFeeWorkflow: automated placement fee calculation and tracking
        - CommissionEngineConfig: configurable commission structure per recruiter
        - TimesheetBillingRecord: contractor timesheet-driven invoicing
        - ClientPortalWhiteLabelAddon: white-label portal per client

    Layer 3 — Commerce & services revenue:
        - AgencyServiceProduct: agency ops consulting, back-office setup, onboarding
        - AgencyServiceOrder: service fulfillment tracker
        - RedeploymentAnalyticsAddon: advanced contractor redeployment tracking

Pricing model:
    Success-based hybrid available:
        - Lower recurring software fee
        - Higher placement / contractor ops fee per outcome
    Standard model:
        - Fixed monthly seats + optional per-outcome transaction fees
"""

import uuid
from django.db import models
from django.conf import settings


# ---------------------------------------------------------------------------
# Agency Plan Definition
# ---------------------------------------------------------------------------

class AgencyPlan(models.Model):
    """
    AgencyOS subscription plan — seat-based with commercial workflow tiers.
    """

    class Tier(models.TextChoices):
        STARTER = "starter", "Starter (1–3 desks)"
        GROWTH = "growth", "Growth (4–15 desks)"
        ENTERPRISE = "enterprise", "Enterprise (unlimited / custom)"

    class PricingModel(models.TextChoices):
        STANDARD = "standard", "Standard (fixed seats + optional per-outcome fees)"
        SUCCESS_BASED = "success_based", "Success-Based (lower SaaS + higher placement fee)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    pricing_model = models.CharField(
        max_length=20, choices=PricingModel.choices, default=PricingModel.STANDARD,
    )

    # LKR-first pricing
    price_monthly_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_annual_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_per_recruiter_seat_monthly_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )
    price_per_account_manager_seat_monthly_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )

    # Success-based variant — lower base fee
    success_base_monthly_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Lower base fee for success-based pricing model.",
    )

    # Stripe references
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, default="")
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")

    # Included seats
    included_recruiter_seats = models.IntegerField(default=1)
    included_account_manager_seats = models.IntegerField(default=1)

    # Plan limits
    job_order_limit = models.IntegerField(
        default=10, help_text="Active job orders. -1 = unlimited.",
    )
    active_contractor_limit = models.IntegerField(
        default=5, help_text="Active contractors under management. -1 = unlimited.",
    )
    client_limit = models.IntegerField(default=10, help_text="-1 = unlimited.")

    # Feature flags
    contractor_ops = models.BooleanField(default=False)
    timesheet_billing = models.BooleanField(default=False)
    placement_fee_workflow = models.BooleanField(default=False)
    commission_engine = models.BooleanField(default=False)
    client_portal = models.BooleanField(default=False)
    white_label_client_portal = models.BooleanField(default=False)
    vms_integration = models.BooleanField(default=False)
    back_office_finance = models.BooleanField(default=False)
    redeployment_analytics = models.BooleanField(default=False)
    advanced_analytics = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)

    trial_days = models.IntegerField(default=14)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_monthly_lkr}/mo"


# ---------------------------------------------------------------------------
# Agency Subscription
# ---------------------------------------------------------------------------

class AgencySubscription(models.Model):
    """
    Active subscription for a staffing agency.
    Tracks seats, billing cycle, gateway, and period.
    """

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        SUSPENDED = "suspended", "Suspended"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    class Gateway(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        PAYHERE = "payhere", "PayHere"
        INVOICE = "invoice", "Invoice / Bank Transfer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.OneToOneField(
        "agencies.Agency", on_delete=models.CASCADE, related_name="subscription",
    )
    plan = models.ForeignKey(
        AgencyPlan, on_delete=models.PROTECT, related_name="subscriptions",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.TRIAL)
    billing_cycle = models.CharField(
        max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY,
    )
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.STRIPE)

    # Seat counts
    recruiter_seats_purchased = models.IntegerField(default=1)
    recruiter_seats_used = models.IntegerField(default=0)
    account_manager_seats_purchased = models.IntegerField(default=1)
    account_manager_seats_used = models.IntegerField(default=0)

    # Pricing model override
    pricing_model = models.CharField(
        max_length=20,
        choices=AgencyPlan.PricingModel.choices,
        default=AgencyPlan.PricingModel.STANDARD,
    )
    negotiated_monthly_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Custom negotiated monthly price. Overrides plan price if set.",
    )

    # Billing period
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    stripe_customer_id = models.CharField(max_length=100, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_subscriptions"

    def __str__(self):
        return f"{self.agency} — {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        return self.status in (self.Status.ACTIVE, self.Status.TRIAL)


# ---------------------------------------------------------------------------
# Placement Fee Workflow (transactional — per-placement revenue tracking)
# ---------------------------------------------------------------------------

class PlacementFeeRule(models.Model):
    """
    Fee calculation rules for permanent and contract placements.
    Configurable per agency and overridable per client.
    """

    class FeeType(models.TextChoices):
        PERCENTAGE_OF_SALARY = "percentage_salary", "% of First-Year Salary"
        FLAT_FEE = "flat_fee", "Flat Placement Fee"
        RETAINER_PLUS_SUCCESS = "retainer_success", "Retainer + Success Fee"
        HOURLY_MARKUP = "hourly_markup", "Hourly Markup % (contractors)"
        DAILY_MARKUP = "daily_markup", "Daily Rate Markup % (contractors)"

    class PlacementType(models.TextChoices):
        PERMANENT = "permanent", "Permanent Placement"
        CONTRACT = "contract", "Contract / Temporary"
        INTERIM = "interim", "Interim / Executive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="fee_rules",
    )
    name = models.CharField(max_length=150)
    placement_type = models.CharField(max_length=20, choices=PlacementType.choices)
    fee_type = models.CharField(max_length=25, choices=FeeType.choices)
    percentage_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Fee % for percentage-based models.",
    )
    flat_fee_lkr = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Fixed fee amount in LKR for flat fee models.",
    )
    markup_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Markup % for hourly/daily contractor billing.",
    )
    guarantee_period_days = models.IntegerField(
        default=90,
        help_text="Replacement guarantee period in days.",
    )
    replacement_policy = models.TextField(blank=True, default="")
    is_default = models.BooleanField(
        default=False, help_text="Default rule for this placement type.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_placement_fee_rules"
        ordering = ["placement_type", "-is_default"]

    def __str__(self):
        return f"{self.agency.name} — {self.name}"


class PlacementFeeRecord(models.Model):
    """
    Tracks a confirmed placement and the fee earned / invoiced.
    Linked to AgencyPlacement (agencies app).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Invoice"
        INVOICED = "invoiced", "Invoiced to Client"
        PARTIAL_PAID = "partial_paid", "Partially Paid"
        PAID = "paid", "Paid in Full"
        IN_GUARANTEE = "in_guarantee", "In Guarantee Period"
        REFUNDED = "refunded", "Refunded (Replacement)"
        WRITTEN_OFF = "written_off", "Written Off"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="placement_fee_records",
    )
    placement = models.OneToOneField(
        "agencies.AgencyPlacement", on_delete=models.CASCADE, related_name="fee_record",
    )
    fee_rule = models.ForeignKey(
        PlacementFeeRule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="placement_records",
    )
    candidate_name = models.CharField(max_length=200)
    client_name = models.CharField(max_length=200)
    role_title = models.CharField(max_length=200)
    placement_date = models.DateField()
    annual_salary_lkr = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
    )
    fee_amount_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    guarantee_expires_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    amount_paid_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_dates = models.JSONField(default=list)
    invoice_reference = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_placement_fee_records"
        ordering = ["-placement_date"]

    def __str__(self):
        return f"{self.agency.name} — {self.candidate_name} placed @ {self.client_name}"


# ---------------------------------------------------------------------------
# Contractor Ops Fees (per-contractor / per-timesheet transactional)
# ---------------------------------------------------------------------------

class ContractorOpsConfig(models.Model):
    """
    Per-contractor operational fee configuration for an agency.
    Applied on top of subscription for contractor management workflows.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.OneToOneField(
        "agencies.Agency", on_delete=models.CASCADE, related_name="contractor_ops_config",
    )
    fee_per_active_contractor_monthly_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Monthly charge per active contractor under management.",
    )
    fee_per_timesheet_submission_lkr = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Charge per approved timesheet submission (if enabled).",
    )
    fee_per_invoice_generated_lkr = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Charge per client invoice generated via platform.",
    )
    included_contractors_in_plan = models.IntegerField(
        default=0, help_text="Contractors included in subscription before per-contractor fee.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_contractor_ops_configs"

    def __str__(self):
        return f"Contractor Ops Config — {self.agency.name}"


# ---------------------------------------------------------------------------
# Commission Engine
# ---------------------------------------------------------------------------

class RecruiterCommissionRule(models.Model):
    """
    Commission calculation rule for a recruiter within an agency.
    Applied to placement fees earned by that recruiter.
    """

    class CommissionModel(models.TextChoices):
        PERCENTAGE_OF_FEE = "percentage_fee", "% of Placement Fee Collected"
        FLAT_PER_PLACEMENT = "flat_placement", "Flat Per Placement"
        TIERED = "tiered", "Tiered (% increases with volume)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="commission_rules",
    )
    recruiter = models.ForeignKey(
        "agencies.AgencyRecruiter", on_delete=models.CASCADE, related_name="commission_rules",
    )
    commission_model = models.CharField(
        max_length=20, choices=CommissionModel.choices, default=CommissionModel.PERCENTAGE_OF_FEE,
    )
    base_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Base commission rate as % of fee collected.",
    )
    flat_amount_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Flat commission per placement (flat model).",
    )
    tiers = models.JSONField(
        default=list,
        help_text=(
            "Tiered commission: [{min_placements: 0, rate_pct: 15}, "
            "{min_placements: 5, rate_pct: 20}, ...]"
        ),
    )
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agency_recruiter_commission_rules"
        ordering = ["-effective_from"]

    def __str__(self):
        return f"{self.recruiter} — {self.commission_model} @ {self.base_rate_pct}%"


# ---------------------------------------------------------------------------
# Client Portal White-label Add-on
# ---------------------------------------------------------------------------

class ClientPortalWhiteLabelAddon(models.Model):
    """
    White-labeled client portal add-on per client relationship.
    Priced per active client portal or as a flat monthly add-on.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="white_label_portals",
    )
    client = models.ForeignKey(
        "agencies.AgencyClient", on_delete=models.CASCADE, related_name="white_label_portals",
    )
    portal_subdomain = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Client-specific subdomain for white-label portal.",
    )
    custom_branding = models.JSONField(
        default=dict,
        help_text="{logo_url, primary_color, font_family, tagline}",
    )
    monthly_fee_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "agency_client_portal_white_label_addons"
        unique_together = [("agency", "client")]

    def __str__(self):
        return f"White-label portal: {self.agency.name} → {self.client}"


# ---------------------------------------------------------------------------
# Agency Professional Services
# ---------------------------------------------------------------------------

class AgencyServiceProduct(models.Model):
    """Professional services sold to staffing agencies on the platform."""

    class ServiceType(models.TextChoices):
        PLATFORM_ONBOARDING = "platform_onboarding", "Platform Onboarding & Setup"
        BACK_OFFICE_SETUP = "back_office_setup", "Back-Office Finance Module Setup"
        VMS_INTEGRATION = "vms_integration", "VMS Integration & Configuration"
        AGENCY_OPS_CONSULTING = "agency_ops_consulting", "Agency Ops Consulting"
        RECRUITER_TRAINING = "recruiter_training", "Recruiter Platform Training"
        PROCESS_AUDIT = "process_audit", "Placement Process Audit"
        COMMISSION_DESIGN = "commission_design", "Commission Structure Design"
        CUSTOM_WORKFLOW = "custom_workflow", "Custom Workflow Development"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    deliverables = models.JSONField(default=list)
    estimated_hours = models.IntegerField(null=True, blank=True)
    price_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_quoted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agency_service_products"
        ordering = ["service_type", "sort_order"]

    def __str__(self):
        return self.name


class AgencyServiceOrder(models.Model):
    """Fulfillment tracker for agency professional services."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        PAID = "paid", "Paid"
        IN_PROGRESS = "in_progress", "In Progress"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="service_orders",
    )
    service = models.ForeignKey(
        AgencyServiceProduct, on_delete=models.PROTECT, related_name="orders",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    amount_paid_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_service_orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agency.name} — {self.service.name} ({self.status})"


# ---------------------------------------------------------------------------
# Invoice & Billing Events
# ---------------------------------------------------------------------------

class AgencyInvoice(models.Model):
    """Consolidated invoice for all AgencyOS charges."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="invoices",
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
        db_table = "agency_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.agency.name} — LKR {self.total_lkr}"


class AgencyBillingEvent(models.Model):
    """Immutable audit log of AgencyOS billing lifecycle events."""

    class EventType(models.TextChoices):
        TRIAL_STARTED = "trial_started", "Trial Started"
        SUBSCRIPTION_CREATED = "subscription_created", "Subscription Created"
        PLAN_UPGRADED = "plan_upgraded", "Plan Upgraded"
        SEAT_ADDED = "seat_added", "Seat Added"
        PAYMENT_SUCCEEDED = "payment_succeeded", "Payment Succeeded"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        SUBSCRIPTION_CANCELLED = "subscription_cancelled", "Subscription Cancelled"
        REFUND_ISSUED = "refund_issued", "Refund Issued"
        PLACEMENT_FEE_INVOICED = "placement_fee_invoiced", "Placement Fee Invoiced"
        PLACEMENT_FEE_RECEIVED = "placement_fee_received", "Placement Fee Received"
        CONTRACTOR_OPS_CHARGED = "contractor_ops_charged", "Contractor Ops Charged"
        SERVICE_ORDER_PLACED = "service_order_placed", "Service Order Placed"
        WHITE_LABEL_ACTIVATED = "white_label_activated", "White-Label Portal Activated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="billing_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    amount_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    plan_before = models.CharField(max_length=30, blank=True, default="")
    plan_after = models.CharField(max_length=30, blank=True, default="")
    gateway_event_id = models.CharField(max_length=200, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agency_billing_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agency.name} — {self.event_type} ({self.created_at:%Y-%m-%d})"
