"""
Feature 9 — Offer & Compensation Operations
Models: 20 total
"""
import uuid
from django.conf import settings
from django.db import models


APPROVAL_STATUS = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("needs_revision", "Needs Revision"),
    ("escalated", "Escalated"),
]


# 1. Offer Approval Matrix
class OfferApprovalMatrix(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_approval_matrices")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    # Rules: list of {threshold_type, threshold_value, required_approvers, approval_order}
    rules = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_offer_approval_matrices"
        ordering = ["name"]


# 2. Compensation Band Guardrail
class CompensationBandGuardrail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="comp_band_guardrails")
    job_family = models.CharField(max_length=150, blank=True, default="")
    job_level = models.CharField(max_length=30, blank=True, default="")
    location = models.CharField(max_length=150, blank=True, default="")
    currency = models.CharField(max_length=10, default="USD")
    band_min = models.DecimalField(max_digits=12, decimal_places=2)
    band_mid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    band_max = models.DecimalField(max_digits=12, decimal_places=2)
    hard_cap = models.BooleanField(default=False)  # block offers above max
    warn_above_mid = models.BooleanField(default=True)
    effective_date = models.DateField(null=True, blank=True)
    expires_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True, default="")  # e.g. Radford, Mercer
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_band_guardrails"
        ordering = ["job_family", "job_level", "location"]


# 3. Location-Based Pay Rule
class LocationPayRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="location_pay_rules")
    location_name = models.CharField(max_length=150)
    country = models.CharField(max_length=100, blank=True, default="")
    state_province = models.CharField(max_length=100, blank=True, default="")
    cost_of_living_index = models.DecimalField(max_digits=6, decimal_places=3, default=1.0)
    pay_multiplier = models.DecimalField(max_digits=6, decimal_places=4, default=1.0)
    currency = models.CharField(max_length=10, default="USD")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_location_pay_rules"
        ordering = ["country", "state_province", "location_name"]


# 4. Sign-On Bonus Rule
class SignOnBonusRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sign_on_bonus_rules")
    name = models.CharField(max_length=255)
    job_level = models.CharField(max_length=30, blank=True, default="")
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    clawback_months = models.IntegerField(default=12)
    clawback_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    requires_approval_above = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conditions = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_sign_on_bonus_rules"
        ordering = ["name"]


# 5. Recurring Bonus Logic
class RecurringBonusRule(models.Model):
    FREQUENCY = [("monthly", "Monthly"), ("quarterly", "Quarterly"), ("semi_annual", "Semi-Annual"), ("annual", "Annual")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="recurring_bonus_rules")
    name = models.CharField(max_length=255)
    bonus_type = models.CharField(max_length=50, default="performance")  # performance/retention/spot/other
    frequency = models.CharField(max_length=20, choices=FREQUENCY, default="annual")
    target_pct_of_salary = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    min_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_pct = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    eligibility_months = models.IntegerField(default=6)  # months employed to be eligible
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_recurring_bonus_rules"
        ordering = ["name"]


# 6. Equity / RSU / ESOP Modeling
class EquityGrant(models.Model):
    GRANT_TYPES = [("rsu", "RSU"), ("iso", "ISO Options"), ("nso", "NSO Options"), ("esop", "ESOP"), ("phantom", "Phantom Equity"), ("sar", "Stock Appreciation Rights")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="equity_grants")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    grant_type = models.CharField(max_length=20, choices=GRANT_TYPES, default="rsu")
    units = models.IntegerField(default=0)
    strike_price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    current_fmv = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    vesting_schedule = models.CharField(max_length=50, default="4yr_1yr_cliff")
    cliff_months = models.IntegerField(default=12)
    total_vest_months = models.IntegerField(default=48)
    grant_value_usd = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_equity_grants"
        ordering = ["-created_at"]


# 7. Relocation Package
class RelocationPackage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="relocation_packages")
    name = models.CharField(max_length=255)
    tier = models.CharField(max_length=20, default="standard")  # standard/premium/executive
    lump_sum_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    includes_moving_service = models.BooleanField(default=False)
    includes_temp_housing = models.BooleanField(default=False)
    temp_housing_days = models.IntegerField(default=30)
    includes_travel_allowance = models.BooleanField(default=False)
    includes_spouse_support = models.BooleanField(default=False)
    repayment_months = models.IntegerField(default=12)
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_relocation_packages"
        ordering = ["tier", "name"]


# 8. Visa / Sponsorship Cost
class VisaSponsorshipCost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="visa_sponsorship_costs")
    visa_type = models.CharField(max_length=50)  # H1B, L1, O1, TN, etc.
    country = models.CharField(max_length=100, blank=True, default="")
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    attorney_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    government_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    processing_weeks = models.IntegerField(default=12)
    premium_processing_available = models.BooleanField(default=False)
    premium_processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_visa_sponsorship_costs"
        ordering = ["visa_type"]


# 9. Internal Equity Check
class InternalEquityCheck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_equity_checks")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    proposed_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    comparable_employees = models.JSONField(default=list)  # [{name/anon_id, salary, level, tenure}]
    avg_peer_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    equity_gap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # proposed - avg
    equity_gap_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    flag_raised = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_equity_checks")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_internal_equity_checks"
        ordering = ["-created_at"]


# 10. Pay Competitiveness Warning
class PayCompetitivenessWarning(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="pay_competitiveness_warnings")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    proposed_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    market_p25 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    market_p50 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    market_p75 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    market_source = models.CharField(max_length=100, blank=True, default="")
    compa_ratio = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    warning_level = models.CharField(max_length=20, default="none")  # none/caution/warning/critical
    warning_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_pay_competitiveness_warnings"
        ordering = ["-created_at"]


# 11. Offer Version History
class OfferVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_versions")
    offer_id = models.UUIDField()  # FK to existing Offer model
    version_number = models.IntegerField(default=1)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    job_title = models.CharField(max_length=255, blank=True, default="")
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sign_on_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_bonus_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    equity_units = models.IntegerField(default=0)
    total_comp_estimate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    details = models.JSONField(default=dict)
    change_summary = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_offer_versions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_offer_versions"
        ordering = ["-created_at"]
        unique_together = [("offer_id", "version_number")]


# 12. Counteroffer Planner
class CounterOfferPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="counteroffer_plans")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    candidate_counter_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    candidate_counter_notes = models.TextField(blank=True, default="")
    our_revised_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    our_revised_bonus = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    our_revised_equity = models.IntegerField(default=0)
    walk_away_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    close_strategy = models.TextField(blank=True, default="")
    outcome = models.CharField(max_length=30, blank=True, default="")  # accepted/declined/pending
    outcome_notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="counteroffer_plans")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_counteroffer_plans"
        ordering = ["-created_at"]


# 13. Approval Audit Trail
class OfferApprovalAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_approval_audits")
    offer_version_id = models.UUIDField(null=True, blank=True)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="offer_approval_audits")
    approval_step = models.IntegerField(default=1)
    action = models.CharField(max_length=20, choices=APPROVAL_STATUS, default="pending")
    note = models.TextField(blank=True, default="")
    actioned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_offer_approval_audits"
        ordering = ["-created_at"]


# 14. Offer Close-Risk Score
class OfferCloseRisk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_close_risks")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0-100
    risk_level = models.CharField(max_length=10, default="low")  # low/medium/high/critical
    risk_factors = models.JSONField(default=list)
    recommended_close_actions = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_offer_close_risks"
        ordering = ["-computed_at"]


# 15. Candidate Decision Deadline
class CandidateDecisionDeadline(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_decision_deadlines")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    deadline = models.DateTimeField()
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    final_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    extended = models.BooleanField(default=False)
    extended_deadline = models.DateTimeField(null=True, blank=True)
    extension_reason = models.TextField(blank=True, default="")
    decision = models.CharField(max_length=20, blank=True, default="")  # accepted/declined/expired/pending
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_candidate_decision_deadlines"
        ordering = ["-created_at"]


# 16. Decline Reason Taxonomy
class DeclineReasonTaxonomy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="decline_reason_taxonomies")
    category = models.CharField(max_length=100)  # compensation/competing_offer/location/timing/role_fit/other
    reason = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_decline_reason_taxonomy"
        ordering = ["category", "reason"]


# 17. Structured Close Plan
class StructuredClosePlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="structured_close_plans")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    close_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="close_plans")
    steps = models.JSONField(default=list)  # [{step, owner, due_date, status, notes}]
    candidate_motivators = models.TextField(blank=True, default="")
    candidate_concerns = models.TextField(blank=True, default="")
    competing_offers = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, default="in_progress")
    closed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_structured_close_plans"
        ordering = ["-created_at"]


# 18. Document Bundle
class OfferDocumentBundle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_document_bundles")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    documents = models.JSONField(default=list)  # [{doc_type, name, url, generated_at}]
    generated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comp_offer_document_bundles"
        ordering = ["-created_at"]


# 19. Compensation Benchmarking Integration
class CompBenchmarkIntegration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="comp_benchmark_integrations")
    provider = models.CharField(max_length=100)  # Radford, Mercer, Levels.fyi, Glassdoor, etc.
    api_endpoint = models.URLField(blank=True, default="")
    api_key_hint = models.CharField(max_length=20, blank=True, default="")  # last 4 chars only
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_frequency_hours = models.IntegerField(default=24)
    data_snapshot = models.JSONField(default=dict)  # cached benchmark data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_benchmark_integrations"
        ordering = ["provider"]


# 20. Preboarding Checklist
class PreboardingChecklist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="preboarding_checklists")
    offer_version_id = models.UUIDField(null=True, blank=True)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    offer_type = models.CharField(max_length=50, blank=True, default="")  # full_time/contract/intern/etc
    items = models.JSONField(default=list)  # [{task, owner, due_date, status}]
    kickoff_triggered_at = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="preboarding_checklists")
    completion_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comp_preboarding_checklists"
        ordering = ["-created_at"]
