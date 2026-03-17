"""Compensation Ops — offer approval matrix, comp bands, equity, relocation."""

import uuid
from django.db import models


class CompensationBand(models.Model):
    """Pay band guardrail for a role/level combination used in offer creation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="compensation_bands")
    name = models.CharField(max_length=255)
    job_family_ref = models.CharField(max_length=255, blank=True, default="", help_text="Human-readable reference")
    level_ref = models.CharField(max_length=100, blank=True, default="")
    geo_zone = models.CharField(max_length=100, blank=True, default="")
    currency = models.CharField(max_length=3, default="USD")
    band_min = models.DecimalField(max_digits=14, decimal_places=2)
    band_mid = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    band_max = models.DecimalField(max_digits=14, decimal_places=2)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compensation_bands"
        ordering = ["name", "geo_zone"]

    def __str__(self):
        return f"{self.name} ({self.geo_zone or 'Global'}) {self.currency}"


class OfferApprovalMatrix(models.Model):
    """Rules that determine which approval chain is required for a given offer."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_approval_matrices")
    name = models.CharField(max_length=255)
    above_band_threshold_pct = models.FloatField(default=0.0,
        help_text="If offer is N% above band max, trigger this matrix")
    department_filter = models.CharField(max_length=150, blank=True, default="")
    level_filter = models.CharField(max_length=100, blank=True, default="")
    requires_cfo_approval = models.BooleanField(default=False)
    requires_chro_approval = models.BooleanField(default=False)
    approval_chain = models.ForeignKey(
        "job_architecture.ApprovalChain", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="offer_matrices"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "offer_approval_matrices"

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class OfferApprovalStep(models.Model):
    """Inline approval step record for a specific offer instance."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("skipped", "Skipped"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_approval_steps")
    offer = models.ForeignKey("applications.Offer", on_delete=models.CASCADE, related_name="approval_steps")
    step_order = models.IntegerField(default=1)
    approver = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="offer_approvals")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "offer_approval_steps"
        ordering = ["offer", "step_order"]

    def __str__(self):
        return f"Offer {self.offer_id} — Step {self.step_order} ({self.status})"


class EquityGrant(models.Model):
    """Equity / RSU / ESOP component of an offer."""

    GRANT_TYPE_CHOICES = [
        ("rsu", "RSU"),
        ("iso", "ISO"),
        ("nso", "NSO"),
        ("esop", "ESOP"),
        ("phantom", "Phantom Stock"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="equity_grants")
    grant_type = models.CharField(max_length=20, choices=GRANT_TYPE_CHOICES, default="rsu")
    units = models.IntegerField(default=0)
    cliff_months = models.IntegerField(default=12)
    vest_months = models.IntegerField(default=48)
    strike_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    estimated_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "equity_grants"

    def __str__(self):
        return f"{self.get_grant_type_display()} — {self.units} units"


class RelocationPackage(models.Model):
    """Relocation package offered to a candidate."""

    TIER_CHOICES = [
        ("none", "None"),
        ("basic", "Basic"),
        ("standard", "Standard"),
        ("premium", "Premium"),
        ("international", "International"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="relocation_packages")
    name = models.CharField(max_length=255)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="standard")
    max_reimbursement = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    includes_house_hunting = models.BooleanField(default=False)
    includes_temporary_housing = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "relocation_packages"

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"


class CompetitivenessAlert(models.Model):
    """Alert when an offer or band falls below market competitiveness threshold."""

    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="competitiveness_alerts")
    alert_type = models.CharField(max_length=100, default="pay_competitiveness")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="warning")
    job_family_ref = models.CharField(max_length=255, blank=True, default="")
    level_ref = models.CharField(max_length=100, blank=True, default="")
    geo_zone = models.CharField(max_length=100, blank=True, default="")
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "competitiveness_alerts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.severity}: {self.alert_type} ({self.tenant.name})"


class OfferVersion(models.Model):
    """Snapshot of an offer at each edit/approval step — full audit trail."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_versions")
    offer = models.ForeignKey("applications.Offer", on_delete=models.CASCADE, related_name="versions")
    version_number = models.IntegerField(default=1)
    snapshot = models.JSONField(default=dict, help_text="Full offer data at this point in time")
    changed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="offer_version_changes")
    change_reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "offer_versions"
        ordering = ["offer", "-version_number"]

    def __str__(self):
        return f"Offer {self.offer_id} v{self.version_number}"


class CounterOfferPlan(models.Model):
    """Records a counter-offer scenario for planning purposes."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("presented", "Presented"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="counter_offer_plans")
    offer = models.ForeignKey("applications.Offer", on_delete=models.CASCADE, related_name="counter_offers")
    counter_base_salary = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    counter_bonus = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    counter_equity_units = models.IntegerField(null=True, blank=True)
    counter_notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="counter_offers")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "counter_offer_plans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Counter Offer for {self.offer_id} ({self.status})"
