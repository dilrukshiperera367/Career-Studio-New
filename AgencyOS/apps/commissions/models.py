"""
Commissions app models.
Commission plans, recruiter/AM splits, perm and contractor commissions,
tiered structures, clawbacks, bonuses, approval workflows, leaderboards.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class CommissionPlan(models.Model):
    """
    A commission plan template applied to one or more recruiters/AMs.
    """

    class PlanType(models.TextChoices):
        PERM_ONLY = "perm_only", "Permanent Placements Only"
        CONTRACT_ONLY = "contract_only", "Contract Spread Only"
        HYBRID = "hybrid", "Hybrid (Perm + Contract)"

    class CommissionModel(models.TextChoices):
        PERCENTAGE_FEE = "percentage_fee", "% of Placement Fee"
        FLAT_AMOUNT = "flat_amount", "Flat Amount per Placement"
        TIERED = "tiered", "Tiered (volume-based)"
        PERCENTAGE_REVENUE = "pct_revenue", "% of Revenue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="commission_plans"
    )
    name = models.CharField(max_length=200)
    plan_type = models.CharField(max_length=20, choices=PlanType.choices, default=PlanType.HYBRID)
    commission_model = models.CharField(
        max_length=30, choices=CommissionModel.choices, default=CommissionModel.PERCENTAGE_FEE
    )
    # Standard rates
    perm_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    contract_spread_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    flat_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # Tiered structure (JSON list of {min_revenue, rate_pct})
    tiers = models.JSONField(default=list)
    # Draw
    monthly_draw = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    draw_is_recoverable = models.BooleanField(default=True)
    # Clawback
    clawback_days = models.IntegerField(default=90)
    clawback_policy = models.TextField(blank=True)
    # Validity
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comm_plan"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_commission_model_display()})"


class RecruiterCommissionAssignment(models.Model):
    """Assigns a commission plan to a specific recruiter or AM."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="recruiter_comm_assignments"
    )
    recruiter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="commission_assignments"
    )
    plan = models.ForeignKey(
        CommissionPlan, on_delete=models.CASCADE, related_name="recruiter_assignments"
    )
    recruiter_split_pct = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    am_split_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    am_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="am_comm_assignments"
    )
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comm_recruiter_assignment"

    def __str__(self):
        return f"{self.recruiter.get_full_name()} – {self.plan.name}"


class CommissionRecord(models.Model):
    """
    An earned commission record for a placement or period.
    """

    class Status(models.TextChoices):
        PROJECTED = "projected", "Projected"
        EARNED = "earned", "Earned"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        CLAWED_BACK = "clawed_back", "Clawed Back"
        ON_HOLD = "on_hold", "On Hold"
        VOIDED = "voided", "Voided"

    class CommissionType(models.TextChoices):
        PERM_PLACEMENT = "perm_placement", "Permanent Placement"
        CONTRACT_SPREAD = "contract_spread", "Contract Spread"
        RETAINER = "retainer", "Retainer"
        BONUS = "bonus", "Bonus"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="commission_records"
    )
    commission_type = models.CharField(max_length=30, choices=CommissionType.choices)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PROJECTED)
    # Who earns it
    recruiter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="commissions_as_recruiter"
    )
    am_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="commissions_as_am"
    )
    plan = models.ForeignKey(
        CommissionPlan, null=True, blank=True, on_delete=models.SET_NULL, related_name="records"
    )
    # Source
    placement = models.ForeignKey(
        "agencies.AgencyPlacement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commissions",
    )
    assignment = models.ForeignKey(
        "contractor_ops.Assignment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commissions",
    )
    # Amounts
    currency = models.CharField(max_length=10, default="USD")
    base_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    gross_commission = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    recruiter_split_pct = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    recruiter_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    am_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Period
    earned_period_start = models.DateField(null=True, blank=True)
    earned_period_end = models.DateField(null=True, blank=True)
    # Approval and payment
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_commissions"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    # Clawback
    clawback_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    clawback_reason = models.TextField(blank=True)
    clawed_back_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comm_record"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recruiter.get_full_name()} – {self.gross_commission} {self.currency} [{self.get_status_display()}]"
