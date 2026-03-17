"""
WorkforceOS Business Model Extension — PEPM / PEPY pricing + module add-ons
+ payroll run fees + implementation & managed services.

This file supplements the existing tenants/enterprise.py (Subscription, Invoice,
BillingHistory) with the full WorkforceOS-specific revenue model:

    Layer 1 — Recurring software revenue (PEPM / PEPY):
        - WorkforceOSPlan: module bundles with per-employee pricing
        - WorkforceSubscriptionDetail: extends Tenant subscription with employee counts
          and module activation flags

    Layer 2 — Transactional / usage revenue:
        - PayrollRunFee: per-payroll-run charge
        - DocumentVolumeFee: per-payslip / bulk document generation
        - IntegrationUsageFee: API / webhook overage charges
        - SMSCreditPack: leave / attendance / payroll notification overages

    Layer 3 — Commerce & services revenue:
        - HRServiceProduct: implementation, training, custom integrations, consulting
        - HRServiceOrder: service fulfillment tracker
        - LearningContentPack: HR/payroll/compliance training packs (company-sponsored seats)

Pricing logic (LKR-first):
    Module tiers:
        Core HR only               — LKR 150–300 PEPM
        Core + Payroll             — LKR 300–500 PEPM
        Full suite (all modules)   — LKR 500–600+ PEPM
    Minimum platform fee applies regardless of employee count.
    Annual contracts: 15–20% discount vs monthly.
"""

import uuid
from django.db import models


# ---------------------------------------------------------------------------
# WorkforceOS Plan (PEPM / PEPY model)
# ---------------------------------------------------------------------------

class WorkforcePlan(models.Model):
    """
    WorkforceOS module bundle definition.
    Priced on a per-employee-per-month (PEPM) basis with a minimum platform fee.
    """

    class Tier(models.TextChoices):
        STARTER = "starter", "Starter (Core HR)"
        GROWTH = "growth", "Growth (Core HR + Payroll + Leave)"
        PROFESSIONAL = "professional", "Professional (Full Suite)"
        ENTERPRISE = "enterprise", "Enterprise (Custom)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    # Base platform fee (minimum charge regardless of employee count)
    platform_fee_monthly_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Minimum monthly platform charge before per-employee pricing.",
    )
    platform_fee_annual_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Annual platform fee (15–20% discount vs 12 × monthly).",
    )

    # Per-employee pricing
    price_pepm_lkr = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Per employee per month charge in LKR.",
    )
    price_pepy_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Per employee per year charge in LKR (annual contract).",
    )

    # Minimum employee count for billing
    min_employees = models.IntegerField(
        default=10, help_text="Minimum billed employee count.",
    )

    # Stripe price IDs
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, default="")
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")

    # Included modules (base plan)
    module_core_hr = models.BooleanField(default=True)
    module_leave_attendance = models.BooleanField(default=False)
    module_onboarding = models.BooleanField(default=False)
    module_payroll = models.BooleanField(default=False)
    module_helpdesk = models.BooleanField(default=False)
    module_performance = models.BooleanField(default=False)
    module_learning = models.BooleanField(default=False)
    module_engagement = models.BooleanField(default=False)
    module_analytics = models.BooleanField(default=False)
    module_internal_mobility = models.BooleanField(default=False)
    module_succession = models.BooleanField(default=False)
    module_sso_scim = models.BooleanField(default=False)
    module_global_workforce = models.BooleanField(default=False)
    module_workforce_planning = models.BooleanField(default=False)
    module_compliance_ai = models.BooleanField(default=False)

    # Trial
    trial_days = models.IntegerField(default=14)

    features = models.JSONField(default=list, help_text="Marketing bullet points.")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_pepm_lkr} PEPM"

    def calculate_monthly_charge_lkr(self, employee_count: int) -> "Decimal":
        """Calculate the monthly bill for a given active employee count."""
        from decimal import Decimal
        billed_count = max(employee_count, self.min_employees)
        charge = Decimal(str(self.platform_fee_monthly_lkr)) + (
            Decimal(str(self.price_pepm_lkr)) * billed_count
        )
        return charge


# ---------------------------------------------------------------------------
# WorkforceOS Module Add-ons
# ---------------------------------------------------------------------------

class WorkforceModuleAddon(models.Model):
    """
    Individual module add-ons purchasable on top of any base plan.
    Priced per-employee-per-month or as a flat monthly add-on.
    """

    class ModuleType(models.TextChoices):
        PERFORMANCE = "performance", "Performance Management"
        LEARNING = "learning", "Learning & Development (LMS)"
        ENGAGEMENT = "engagement", "Employee Engagement & Surveys"
        ANALYTICS = "analytics", "People Analytics Dashboard"
        INTERNAL_MOBILITY = "internal_mobility", "Internal Mobility & Job Board"
        SUCCESSION = "succession", "Succession Planning"
        SSO_SCIM = "sso_scim", "SSO / SCIM Enterprise Identity"
        AUDIT_COMPLIANCE = "audit_compliance", "Audit Trails & Compliance Pack"
        CUSTOM_WORKFLOWS = "custom_workflows", "Custom Workflow Builder"
        COUNTRY_POLICY = "country_policy", "Country / Policy Pack"
        GLOBAL_WORKFORCE = "global_workforce", "Global Workforce & Visa Tracking"
        WORKFORCE_PLANNING = "workforce_planning", "Workforce Planning & Forecasting"
        COMPLIANCE_AI = "compliance_ai", "Compliance AI Assistant"
        CONTINGENT_OPS = "contingent_ops", "Contingent / Contract Worker Ops"
        TOTAL_REWARDS = "total_rewards", "Total Rewards & Comp Management"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module_type = models.CharField(max_length=30, choices=ModuleType.choices, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    pricing_model = models.CharField(
        max_length=20,
        choices=[("pepm", "Per Employee Per Month"), ("flat", "Flat Monthly Fee")],
        default="pepm",
    )
    price_pepm_lkr = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Per-employee add-on price (if PEPM pricing model).",
    )
    price_flat_monthly_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Flat monthly add-on price (if flat pricing model).",
    )
    price_flat_annual_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, default="")
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_module_addons"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name}"


class TenantModuleAddon(models.Model):
    """Tracks which module add-ons a tenant has activated."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"
        PENDING = "pending", "Pending Activation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="module_addons",
    )
    module = models.ForeignKey(
        WorkforceModuleAddon, on_delete=models.PROTECT, related_name="tenant_activations",
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
        db_table = "workforce_tenant_module_addons"
        unique_together = [("tenant", "module")]

    def __str__(self):
        return f"{self.tenant} + {self.module.name} ({self.status})"


# ---------------------------------------------------------------------------
# Employee Count Snapshot (drives PEPM billing)
# ---------------------------------------------------------------------------

class EmployeeCountSnapshot(models.Model):
    """
    Monthly snapshot of active employee count per tenant.
    Used as the billing basis for PEPM charges.
    Captured by a Celery beat task at start of each billing period.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="employee_count_snapshots",
    )
    snapshot_date = models.DateField()
    active_employees = models.IntegerField()
    billed_employees = models.IntegerField(
        help_text="max(active_employees, plan.min_employees)",
    )
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_employee_count_snapshots"
        ordering = ["-snapshot_date"]
        unique_together = [("tenant", "billing_period_start")]

    def __str__(self):
        return f"{self.tenant} — {self.billed_employees} billed @ {self.snapshot_date}"


# ---------------------------------------------------------------------------
# Payroll Run Fees (per-run transactional charge)
# ---------------------------------------------------------------------------

class PayrollRunFeeConfig(models.Model):
    """
    Per-payroll-run fee configuration.
    Charged each time a payroll run is executed beyond the plan-included runs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    runs_included_monthly = models.IntegerField(
        default=1, help_text="Payroll runs included in base plan per month.",
    )
    fee_per_additional_run_lkr = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Charge per payroll run beyond the included monthly quota.",
    )
    fee_per_payslip_lkr = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Optional per-payslip charge for high-volume tenants.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_payroll_run_fee_configs"

    def __str__(self):
        return f"{self.name} — LKR {self.fee_per_additional_run_lkr}/run"


class PayrollRunFeeRecord(models.Model):
    """Records each payroll run charge against a tenant."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INVOICED = "invoiced", "Invoiced"
        PAID = "paid", "Paid"
        WAIVED = "waived", "Waived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="payroll_run_fees",
    )
    run_date = models.DateField()
    payslip_count = models.IntegerField()
    is_included_in_plan = models.BooleanField(
        default=False, help_text="True if within monthly plan quota (no charge).",
    )
    fee_charged_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    invoice = models.ForeignKey(
        "WorkforceInvoice", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payroll_run_fees",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_payroll_run_fee_records"
        ordering = ["-run_date"]

    def __str__(self):
        return f"{self.tenant} payroll run {self.run_date} — LKR {self.fee_charged_lkr}"


# ---------------------------------------------------------------------------
# HR Professional Services (Layer 3)
# ---------------------------------------------------------------------------

class HRServiceProduct(models.Model):
    """
    One-off professional services for WorkforceOS customers.
    Implementation, training, consulting, managed payroll support.
    """

    class ServiceType(models.TextChoices):
        IMPLEMENTATION = "implementation", "Platform Implementation & Setup"
        PAYROLL_SETUP = "payroll_setup", "Payroll Configuration & Setup"
        DATA_MIGRATION = "data_migration", "HR Data Migration"
        ADMIN_TRAINING = "admin_training", "HR Admin / Payroll Training"
        MANAGER_TRAINING = "manager_training", "Manager & Self-Service Training"
        CUSTOM_REPORT = "custom_report", "Custom Report Development"
        CUSTOM_INTEGRATION = "custom_integration", "Custom Integration Development"
        COMPLIANCE_REVIEW = "compliance_review", "HR Compliance Review"
        POLICY_PACK = "policy_pack", "HR Policy Pack (country-specific)"
        MANAGED_PAYROLL = "managed_payroll", "Managed Payroll Processing (ongoing)"
        SUPPORT_SLA = "support_sla", "Dedicated Support SLA (annual)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    deliverables = models.JSONField(default=list)
    estimated_hours = models.IntegerField(null=True, blank=True)
    price_lkr = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Fixed price. 0 = quoted on request.",
    )
    is_quoted = models.BooleanField(
        default=False, help_text="If True, price is determined per quote.",
    )
    is_recurring = models.BooleanField(
        default=False, help_text="If True, this is a monthly managed service.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_hr_service_products"
        ordering = ["service_type", "sort_order"]

    def __str__(self):
        return self.name


class HRServiceOrder(models.Model):
    """Service fulfillment tracker for HR professional services."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        PAID = "paid", "Paid — Awaiting Kickoff"
        IN_PROGRESS = "in_progress", "In Progress"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="hr_service_orders",
    )
    service = models.ForeignKey(
        HRServiceProduct, on_delete=models.PROTECT, related_name="orders",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    amount_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    amount_paid_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    kickoff_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    deliverables_submitted = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_hr_service_orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant} — {self.service.name} ({self.status})"


# ---------------------------------------------------------------------------
# Invoice & Billing Events
# ---------------------------------------------------------------------------

class WorkforceInvoice(models.Model):
    """Invoice covering all WorkforceOS charges for a billing period."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="workforce_invoices",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    billed_employees = models.IntegerField(default=0)
    line_items = models.JSONField(
        default=list,
        help_text=(
            "Each item: {type, description, qty, unit_price_lkr, amount_lkr}. "
            "Types: subscription, pepm_charge, module_addon, payroll_run_fee, "
            "service, document_volume, comms_credits."
        ),
    )
    subtotal_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    discount_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_digits=10, choices=Status.choices, default=Status.DRAFT)
    payment_gateway = models.CharField(max_length=30, blank=True, default="")
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    stripe_invoice_id = models.CharField(max_length=100, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.tenant} — LKR {self.total_lkr}"


class WorkforceBillingEvent(models.Model):
    """Immutable audit log extending WorkforceOS billing events."""

    class EventType(models.TextChoices):
        TRIAL_STARTED = "trial_started", "Trial Started"
        TRIAL_EXPIRED = "trial_expired", "Trial Expired"
        SUBSCRIPTION_CREATED = "subscription_created", "Subscription Created"
        PLAN_UPGRADED = "plan_upgraded", "Plan Upgraded"
        PLAN_DOWNGRADED = "plan_downgraded", "Plan Downgraded"
        MODULE_ACTIVATED = "module_activated", "Module Add-on Activated"
        MODULE_DEACTIVATED = "module_deactivated", "Module Add-on Deactivated"
        EMPLOYEE_COUNT_CHANGED = "employee_count_changed", "Employee Count Changed"
        PAYMENT_SUCCEEDED = "payment_succeeded", "Payment Succeeded"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        SUBSCRIPTION_CANCELLED = "subscription_cancelled", "Subscription Cancelled"
        REFUND_ISSUED = "refund_issued", "Refund Issued"
        INVOICE_GENERATED = "invoice_generated", "Invoice Generated"
        PAYROLL_RUN_CHARGED = "payroll_run_charged", "Payroll Run Charged"
        SERVICE_ORDER_PLACED = "service_order_placed", "Service Order Placed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="workforce_billing_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    amount_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    plan_before = models.CharField(max_length=30, blank=True, default="")
    plan_after = models.CharField(max_length=30, blank=True, default="")
    employee_count_before = models.IntegerField(null=True, blank=True)
    employee_count_after = models.IntegerField(null=True, blank=True)
    gateway_event_id = models.CharField(max_length=200, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_billing_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant} — {self.event_type} ({self.created_at:%Y-%m-%d})"
