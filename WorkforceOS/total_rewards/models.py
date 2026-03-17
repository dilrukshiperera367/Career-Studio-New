"""
Total Rewards — compensation bands, merit cycles, equity, total rewards statements, pay equity.
"""

import uuid
from django.db import models
from django.conf import settings


class CompensationBand(models.Model):
    """Salary band / pay range for a grade or position."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='comp_bands')
    name = models.CharField(max_length=200)
    grade = models.CharField(max_length=50, blank=True)
    band = models.CharField(max_length=50, blank=True)
    job_family = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=3, default='LKR')
    min_salary = models.DecimalField(max_digits=14, decimal_places=2)
    mid_salary = models.DecimalField(max_digits=14, decimal_places=2)
    max_salary = models.DecimalField(max_digits=14, decimal_places=2)
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    market_data_source = models.CharField(max_length=200, blank=True)
    market_percentile = models.IntegerField(default=50, help_text='Target market positioning (50 = median)')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'compensation_bands'
        ordering = ['grade', 'band', 'name']

    def __str__(self):
        return f"{self.name} ({self.min_salary}–{self.max_salary} {self.currency})"

    @property
    def spread(self):
        if self.min_salary and self.max_salary:
            return round(float((self.max_salary - self.min_salary) / self.min_salary * 100), 1)
        return None


class MeritCycle(models.Model):
    """Annual or mid-year merit/salary review cycle."""
    STATUS_CHOICES = [
        ('planning', 'Planning'), ('manager_input', 'Manager Input'),
        ('calibration', 'Calibration'), ('approval', 'Approval'),
        ('finalized', 'Finalized'), ('communicated', 'Communicated'), ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='merit_cycles')
    name = models.CharField(max_length=200)
    cycle_year = models.IntegerField()
    cycle_type = models.CharField(
        max_length=20, default='annual',
        choices=[('annual', 'Annual'), ('mid_year', 'Mid-Year'), ('off_cycle', 'Off-Cycle')]
    )
    budget_pool_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                           help_text='Total merit budget as % of payroll')
    effective_date = models.DateField()
    manager_input_deadline = models.DateField(null=True, blank=True)
    calibration_deadline = models.DateField(null=True, blank=True)
    approval_deadline = models.DateField(null=True, blank=True)
    communication_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    guidelines = models.JSONField(default=dict,
        help_text='{"exceeds":0.06,"meets":0.04,"below":0.00,"promo_additional":0.08}')
    total_eligible_employees = models.IntegerField(default=0)
    total_budget_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    total_allocated_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'merit_cycles'
        ordering = ['-cycle_year']

    def __str__(self):
        return f"{self.name} ({self.cycle_year})"


class MeritRecommendation(models.Model):
    """Manager's merit/bonus recommendation for a single employee within a cycle."""
    RECOMMENDATION_TYPES = [
        ('merit', 'Merit Increase'), ('bonus', 'Bonus'), ('promotion', 'Promotion + Merit'),
        ('no_change', 'No Change'), ('demotion', 'Demotion'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('calibrated', 'Calibrated'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='merit_recommendations')
    cycle = models.ForeignKey(MeritCycle, on_delete=models.CASCADE, related_name='recommendations')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='merit_recommendations')
    recommender = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE,
                                     related_name='merit_recommendations_given')
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES, default='merit')
    current_salary = models.DecimalField(max_digits=14, decimal_places=2)
    recommended_salary = models.DecimalField(max_digits=14, decimal_places=2)
    merit_increase_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bonus_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    performance_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    compa_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                       help_text='Salary / midpoint of band')
    justification = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    calibrated_salary = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    calibrated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'merit_recommendations'
        unique_together = ['cycle', 'employee']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} — {self.recommendation_type} ({self.cycle})"


class EquityGrant(models.Model):
    """Stock option or equity grant record."""
    GRANT_TYPES = [
        ('stock_option', 'Stock Option'), ('rsu', 'RSU'), ('phantom', 'Phantom Stock'),
        ('sar', 'Stock Appreciation Right'), ('espp', 'ESPP'),
    ]
    STATUS_CHOICES = [
        ('granted', 'Granted'), ('vesting', 'Vesting'), ('vested', 'Vested'),
        ('exercised', 'Exercised'), ('forfeited', 'Forfeited'), ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='equity_grants')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='equity_grants')
    grant_type = models.CharField(max_length=20, choices=GRANT_TYPES)
    grant_date = models.DateField()
    units_granted = models.IntegerField()
    grant_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    vesting_schedule = models.JSONField(default=list,
        help_text='[{"date":"2025-01-01","units":250,"vested":false}]')
    cliff_months = models.IntegerField(default=12)
    total_vesting_months = models.IntegerField(default=48)
    units_vested = models.IntegerField(default=0)
    units_exercised = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='granted')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'equity_grants'
        ordering = ['-grant_date']

    def __str__(self):
        return f"{self.grant_type}: {self.units_granted} units for {self.employee}"


class TotalRewardsStatement(models.Model):
    """Annual total rewards statement summarising all compensation elements for one employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='total_rewards_statements')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='total_rewards_statements')
    statement_year = models.IntegerField()
    base_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_bonus = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    equity_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    employer_benefits_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    employer_statutory_value = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                                    help_text='EPF/ETF employer portion')
    other_allowances = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_compensation = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='LKR')
    breakdown = models.JSONField(default=dict, help_text='Full itemised breakdown')
    pdf_url = models.CharField(max_length=500, blank=True)
    is_visible_to_employee = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'total_rewards_statements'
        unique_together = ['tenant', 'employee', 'statement_year']
        ordering = ['-statement_year']

    def __str__(self):
        return f"TRS {self.statement_year} — {self.employee}"


class PayEquityAnalysis(models.Model):
    """Periodic pay equity analysis snapshot."""
    ANALYSIS_TYPES = [
        ('gender', 'Gender Pay Gap'), ('ethnicity', 'Ethnicity Pay Gap'),
        ('grade', 'Grade Pay Spread'), ('tenure', 'Tenure vs Pay'), ('department', 'Department Pay Spread'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='pay_equity_analyses')
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_TYPES)
    analysis_date = models.DateField()
    scope = models.JSONField(default=dict, help_text='{"department":"Engineering","grade":"G4"}')
    results = models.JSONField(default=dict,
        help_text='{"group_a":{"avg_salary":...,"median_salary":...,"count":...},...}')
    gap_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                   help_text='Overall pay gap % (positive = group A earns more)')
    risk_level = models.CharField(
        max_length=10, default='low',
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    )
    recommended_actions = models.JSONField(default=list)
    run_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'pay_equity_analyses'
        ordering = ['-analysis_date']

    def __str__(self):
        return f"Pay Equity ({self.analysis_type}) {self.analysis_date}"


# ============ FEATURE 5: BONUS, INCENTIVE & COMP REVIEW UPGRADES ============

class BonusIncentivePlan(models.Model):
    """Bonus / incentive plan definition for a given year and eligibility scope."""
    PLAN_TYPES = [
        ('annual_bonus', 'Annual Bonus'), ('quarterly_bonus', 'Quarterly Bonus'),
        ('spot_award', 'Spot Award'), ('retention_bonus', 'Retention Bonus'),
        ('performance_incentive', 'Performance Incentive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='bonus_incentive_plans')
    name = models.CharField(max_length=200)
    plan_type = models.CharField(max_length=30, choices=PLAN_TYPES)
    plan_year = models.IntegerField()
    eligibility_criteria = models.JSONField(default=dict, blank=True,
        help_text='{"grades": [...], "departments": [...], "min_tenure_months": 6}')
    target_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        help_text='Target bonus as % of annual salary')
    max_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    funding_formula = models.JSONField(default=dict, blank=True,
        help_text='{"company_performance_weight":0.5,"individual_performance_weight":0.5}')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'bonus_incentive_plans'
        ordering = ['-plan_year', 'name']

    def __str__(self):
        return f"{self.name} ({self.plan_type}, {self.plan_year})"


class BonusIncentiveEntry(models.Model):
    """Individual bonus / incentive award entry for an employee."""
    STATUS_CHOICES = [
        ('calculated', 'Calculated'), ('manager_review', 'Manager Review'),
        ('approved', 'Approved'), ('paid', 'Paid'), ('withheld', 'Withheld'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='bonus_incentive_entries')
    plan = models.ForeignKey(BonusIncentivePlan, on_delete=models.CASCADE, related_name='entries')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='bonus_incentive_entries')
    target_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    awarded_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='LKR')
    performance_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    company_performance_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    individual_performance_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    calculation_breakdown = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='calculated')
    manager_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'bonus_incentive_entries'
        ordering = ['-created_at']
        unique_together = ['plan', 'employee']

    def __str__(self):
        return f"{self.employee} — {self.plan.name}: {self.awarded_amount} ({self.status})"


class ManagerCompReviewWorkspace(models.Model):
    """Manager's workspace for reviewing and adjusting team compensation during a merit cycle."""
    STATUS_CHOICES = [
        ('open', 'Open'), ('submitted', 'Submitted'), ('calibrated', 'Calibrated'),
        ('locked', 'Locked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='manager_comp_review_workspaces')
    cycle = models.ForeignKey(MeritCycle, on_delete=models.CASCADE, related_name='manager_workspaces')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='comp_review_workspaces')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    budget_allocated = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    budget_used = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    team_snapshot = models.JSONField(default=list, blank=True,
        help_text='Snapshot of team members with salary data at cycle open')
    submitted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'manager_comp_review_workspaces'
        unique_together = ['cycle', 'manager']
        ordering = ['-created_at']

    def __str__(self):
        return f"Comp Review: {self.manager} — {self.cycle} ({self.status})"


class CompChangeApproval(models.Model):
    """Multi-level approval record for a compensation change (merit/off-cycle)."""
    APPROVAL_STATUSES = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('escalated', 'Escalated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='comp_change_approvals')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='comp_change_approvals')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='comp_approvals_given')
    approval_level = models.IntegerField(default=1, help_text='1=Line Manager, 2=HR, 3=Finance, etc.')
    change_type = models.CharField(max_length=50, blank=True)
    proposed_salary = models.DecimalField(max_digits=14, decimal_places=2)
    current_salary = models.DecimalField(max_digits=14, decimal_places=2)
    increase_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    justification = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=APPROVAL_STATUSES, default='pending')
    decision_notes = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'total_rewards'
        db_table = 'comp_change_approvals'
        ordering = ['-created_at']

    def __str__(self):
        return f"CompApproval L{self.approval_level}: {self.employee} — {self.status}"
