"""
Workforce Planning & Org Design models.

Covers all 15 feature areas:
  1.  Annual / quarterly headcount planning          → HeadcountPlan (Q-period support)
  2.  Position budgeting & approved FTE controls     → PositionBudget
  3.  Vacancy planning & backfill workflows          → VacancyPlan
  4.  Workforce scenario planning                    → WorkforceScenario + ScenarioLineItem
  5.  Future org-chart modeling                      → OrgDesignScenario + OrgDesignNode
  6.  Span-of-control & management-layer analysis    → SpanOfControlSnapshot
  7.  Workforce cost forecasting                     → WorkforceCostForecast + CostForecastLineItem
  8.  Department budget vs actual headcount          → DepartmentBudgetActual
  9.  Location / site workforce planning             → LocationWorkforcePlan
  10. Contractor vs FTE mix planning                 → WorkforceMixPlan
  11. Critical role mapping                          → CriticalRoleMapping (+ links to core_hr.CriticalRole)
  12. Succession coverage planning                   → SuccessionCoveragePlan
  13. Skills demand forecasting                      → SkillsDemandForecast + SkillsDemandLineItem
  14. Requisition handoff to TalentOS                → HiringRequisition (extended with talentOS fields)
  15. Reorg / change-management workflows            → ReorgWorkflow + ReorgWorkflowTask
"""

import uuid
from django.db import models
from django.conf import settings


# ---------------------------------------------------------------------------
# 1. Headcount Plan  (annual + quarterly periods)
# ---------------------------------------------------------------------------

class HeadcountPlan(models.Model):
    """Approved headcount plan per department per period (annual or quarterly)."""

    PERIOD_CHOICES = [
        ('annual', 'Annual'),
        ('q1', 'Q1'),
        ('q2', 'Q2'),
        ('q3', 'Q3'),
        ('q4', 'Q4'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('locked', 'Locked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='headcount_plans'
    )
    name = models.CharField(max_length=200)
    plan_year = models.IntegerField()
    period = models.CharField(max_length=6, choices=PERIOD_CHOICES, default='annual')
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='headcount_plans'
    )
    company = models.ForeignKey(
        'core_hr.Company', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='headcount_plans'
    )
    planned_headcount = models.IntegerField()
    current_headcount = models.IntegerField(default=0)
    approved_headcount = models.IntegerField(null=True, blank=True)
    open_requisitions = models.IntegerField(
        default=0, help_text='Auto-computed count of open reqs against this plan'
    )
    budget_amount = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_headcount_plans'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'headcount_plans'
        unique_together = [['tenant', 'name', 'plan_year', 'period']]

    def __str__(self):
        return f"{self.name} ({self.plan_year} / {self.period})"

    @property
    def headcount_gap(self):
        """Planned minus current headcount."""
        return self.planned_headcount - self.current_headcount

    @property
    def budget_utilisation_pct(self):
        """Percentage of planned positions currently filled."""
        if self.planned_headcount == 0:
            return 0
        return round(self.current_headcount / self.planned_headcount * 100, 1)


# ---------------------------------------------------------------------------
# 2. Position Budget  (approved FTE controls)
# ---------------------------------------------------------------------------

class PositionBudget(models.Model):
    """Position-level budget allocation with FTE controls."""

    SUCCESSION_READINESS_CHOICES = [
        ('ready_now', 'Ready Now'),
        ('ready_12m', 'Ready in 12 months'),
        ('ready_24m', 'Ready in 24 months'),
        ('gap', 'Gap'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='position_budgets'
    )
    position = models.ForeignKey(
        'core_hr.Position', on_delete=models.CASCADE,
        related_name='position_budgets'
    )
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='position_budgets'
    )
    budget_year = models.IntegerField()
    allocated_headcount = models.IntegerField(default=1)
    filled_headcount = models.IntegerField(default=0)
    # FTE controls
    approved_fte = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00,
        help_text='Approved full-time equivalents for this position'
    )
    used_fte = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text='Currently used FTE (actual employees)'
    )
    budgeted_salary = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    actual_salary_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Actual YTD salary cost for this position'
    )
    currency = models.CharField(max_length=3, default='LKR')
    is_critical_role = models.BooleanField(default=False)
    succession_readiness = models.CharField(
        max_length=15, choices=SUCCESSION_READINESS_CHOICES, default='gap'
    )
    freeze_hiring = models.BooleanField(
        default=False, help_text='Hiring freeze flag — blocks new requisitions'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'position_budgets'
        unique_together = [['position', 'budget_year']]

    def __str__(self):
        return f"{self.position} — {self.budget_year}"

    @property
    def fte_variance(self):
        return round(float(self.approved_fte) - float(self.used_fte), 2)

    @property
    def budget_variance(self):
        if self.budgeted_salary is None or self.actual_salary_cost is None:
            return None
        return round(float(self.budgeted_salary) - float(self.actual_salary_cost), 2)


# ---------------------------------------------------------------------------
# 3. Vacancy Plan  (vacancy planning + backfill workflows)
# ---------------------------------------------------------------------------

class VacancyPlan(models.Model):
    """Tracks planned, active, and backfill vacancies."""

    VACANCY_TYPE_CHOICES = [
        ('new_role', 'New Role'),
        ('backfill', 'Backfill'),
        ('expansion', 'Expansion'),
        ('replacement', 'Replacement'),
    ]

    STATUS_CHOICES = [
        ('anticipated', 'Anticipated'),
        ('approved', 'Approved'),
        ('open', 'Open'),
        ('in_recruitment', 'In Recruitment'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='vacancy_plans'
    )
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vacancy_plans'
    )
    position = models.ForeignKey(
        'core_hr.Position', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vacancy_plans'
    )
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.CASCADE,
        related_name='vacancy_plans'
    )
    vacancy_type = models.CharField(max_length=20, choices=VACANCY_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='anticipated')
    # Backfill-specific
    backfill_for = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='backfill_vacancies',
        help_text='Employee being replaced (backfill only)'
    )
    expected_vacancy_date = models.DateField(null=True, blank=True)
    target_fill_date = models.DateField(null=True, blank=True)
    actual_fill_date = models.DateField(null=True, blank=True)
    # Requisition handoff
    requisition = models.OneToOneField(
        'HiringRequisition', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vacancy_plan'
    )
    hiring_manager = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_vacancies'
    )
    estimated_salary = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'vacancy_plans'
        ordering = ['expected_vacancy_date']

    def __str__(self):
        return f"{self.vacancy_type} vacancy — {self.department} ({self.status})"


# ---------------------------------------------------------------------------
# 4. Workforce Scenario Planning
# ---------------------------------------------------------------------------

class WorkforceScenario(models.Model):
    """What-if workforce scenario: growth, freeze, restructure, downsizing."""

    SCENARIO_TYPE_CHOICES = [
        ('growth', 'Growth'),
        ('freeze', 'Hiring Freeze'),
        ('restructure', 'Restructure'),
        ('downsizing', 'Downsizing'),
        ('acquisition', 'Acquisition / Merger'),
        ('spin_off', 'Spin-off'),
        ('custom', 'Custom'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('modelling', 'Modelling'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('implemented', 'Implemented'),
        ('discarded', 'Discarded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='workforce_scenarios'
    )
    name = models.CharField(max_length=200)
    scenario_type = models.CharField(max_length=20, choices=SCENARIO_TYPE_CHOICES)
    description = models.TextField(blank=True)
    base_year = models.IntegerField()
    horizon_years = models.IntegerField(
        default=3, help_text='Planning horizon in years'
    )
    assumptions = models.JSONField(
        default=dict,
        help_text='Key assumptions: attrition rate, growth %, cost per hire, etc.'
    )
    # Computed totals (denormalised for fast reads)
    projected_headcount = models.IntegerField(null=True, blank=True)
    projected_cost = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    headcount_delta = models.IntegerField(
        null=True, blank=True,
        help_text='Projected headcount minus current headcount'
    )
    cost_delta = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    # Approval chain
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_workforce_scenarios'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_workforce_scenarios'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'workforce_scenarios'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.scenario_type}, {self.base_year})"


class ScenarioLineItem(models.Model):
    """Detailed year-by-year line item for a workforce scenario."""

    CHANGE_TYPE_CHOICES = [
        ('hire', 'New Hire'),
        ('terminate', 'Termination'),
        ('transfer', 'Transfer'),
        ('promote', 'Promotion'),
        ('convert_fte', 'Convert to FTE'),
        ('convert_contractor', 'Convert to Contractor'),
        ('restructure', 'Restructure'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='scenario_line_items'
    )
    scenario = models.ForeignKey(
        WorkforceScenario, on_delete=models.CASCADE,
        related_name='line_items'
    )
    year = models.IntegerField()
    quarter = models.IntegerField(
        null=True, blank=True,
        help_text='1-4 for quarterly breakdown; null = annual'
    )
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    position = models.ForeignKey(
        'core_hr.Position', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    headcount_change = models.IntegerField(
        help_text='Positive = additions, negative = reductions'
    )
    cost_impact = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    currency = models.CharField(max_length=3, default='LKR')
    rationale = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'scenario_line_items'
        ordering = ['year', 'quarter']

    def __str__(self):
        return f"{self.scenario} | {self.year} | {self.change_type} ({self.headcount_change:+d})"


# ---------------------------------------------------------------------------
# 5. Org Design Scenario  (future org-chart modeling)
# ---------------------------------------------------------------------------

class OrgDesignScenario(models.Model):
    """Future org-chart scenario with node-level changes."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('discarded', 'Discarded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='org_design_scenarios'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Snapshot of current structure stored as JSON for offline comparison
    base_snapshot = models.JSONField(
        default=dict,
        help_text='Current org structure snapshot at time of scenario creation'
    )
    proposed_changes = models.JSONField(
        default=list,
        help_text='High-level list of proposed org changes (legacy / summary field)'
    )
    cost_impact = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    headcount_impact = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    linked_scenario = models.ForeignKey(
        WorkforceScenario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='org_scenarios',
        help_text='Optional link to parent workforce scenario'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'org_design_scenarios'

    def __str__(self):
        return self.name


class OrgDesignNode(models.Model):
    """A single node (department/role) change within an org design scenario."""

    NODE_TYPE_CHOICES = [
        ('department', 'Department'),
        ('team', 'Team'),
        ('position', 'Position'),
        ('role', 'Role'),
    ]

    CHANGE_ACTION_CHOICES = [
        ('create', 'Create'),
        ('delete', 'Delete'),
        ('rename', 'Rename'),
        ('move', 'Move (re-parent)'),
        ('merge', 'Merge'),
        ('split', 'Split'),
        ('elevate', 'Elevate Layer'),
        ('flatten', 'Flatten Layer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='org_design_nodes'
    )
    scenario = models.ForeignKey(
        OrgDesignScenario, on_delete=models.CASCADE,
        related_name='nodes'
    )
    node_type = models.CharField(max_length=15, choices=NODE_TYPE_CHOICES)
    change_action = models.CharField(max_length=15, choices=CHANGE_ACTION_CHOICES)
    # References to real objects (nullable because they may not exist yet)
    ref_department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    ref_position = models.ForeignKey(
        'core_hr.Position', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    new_name = models.CharField(max_length=200, blank=True)
    new_parent_department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    headcount_impact = models.IntegerField(default=0)
    cost_impact = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    rationale = models.TextField(blank=True)
    sequence = models.IntegerField(
        default=0, help_text='Execution order within the scenario'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'org_design_nodes'
        ordering = ['sequence']

    def __str__(self):
        return f"{self.scenario} | {self.change_action} {self.node_type} ({self.new_name or 'unnamed'})"


# ---------------------------------------------------------------------------
# 6. Span-of-Control Snapshot
# ---------------------------------------------------------------------------

class SpanOfControlSnapshot(models.Model):
    """Point-in-time snapshot of span of control and management layers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='span_snapshots'
    )
    snapshot_date = models.DateField()
    company = models.ForeignKey(
        'core_hr.Company', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='span_snapshots'
    )
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='span_snapshots',
        help_text='Null = company-wide snapshot'
    )
    manager = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='span_snapshots'
    )
    direct_report_count = models.IntegerField(default=0)
    total_report_count = models.IntegerField(
        default=0, help_text='Including indirect reports'
    )
    management_layer = models.IntegerField(
        help_text='Depth from CEO: 0 = CEO, 1 = C-suite, 2 = VP, etc.'
    )
    avg_span_company = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Company-wide average span for this snapshot'
    )
    avg_span_department = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    managers_over_span = models.IntegerField(
        default=0, help_text='Managers exceeding target span threshold'
    )
    managers_under_span = models.IntegerField(
        default=0, help_text='Managers below minimum span threshold'
    )
    target_span_min = models.IntegerField(default=4)
    target_span_max = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'span_of_control_snapshots'
        ordering = ['-snapshot_date']
        unique_together = [['tenant', 'snapshot_date', 'manager']]

    def __str__(self):
        mgr = str(self.manager) if self.manager else 'Company-wide'
        return f"Span Snapshot {self.snapshot_date} — {mgr} ({self.direct_report_count} direct reports)"


# ---------------------------------------------------------------------------
# 7. Workforce Cost Forecast
# ---------------------------------------------------------------------------

class WorkforceCostForecast(models.Model):
    """Multi-year workforce cost forecast."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('final', 'Final'),
        ('approved', 'Approved'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='cost_forecasts'
    )
    name = models.CharField(max_length=200)
    company = models.ForeignKey(
        'core_hr.Company', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cost_forecasts'
    )
    forecast_year = models.IntegerField()
    horizon_years = models.IntegerField(default=3)
    # Inputs / assumptions
    current_headcount = models.IntegerField(default=0)
    planned_headcount = models.IntegerField(default=0)
    avg_salary = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    salary_increase_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        help_text='Annual merit / COLA increase %'
    )
    benefits_load_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.00,
        help_text='Benefits as % of salary'
    )
    attrition_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00
    )
    cost_per_hire = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    contractor_spend = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    # Outputs (computed and cached)
    total_salary_cost = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    total_benefits_cost = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    total_recruitment_cost = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    total_workforce_cost = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_cost_forecasts'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'workforce_cost_forecasts'
        ordering = ['-forecast_year']

    def __str__(self):
        return f"{self.name} ({self.forecast_year})"

    def compute_totals(self):
        """Calculate and cache total workforce costs from inputs."""
        if not self.avg_salary or not self.planned_headcount:
            return
        salary = float(self.avg_salary) * self.planned_headcount
        benefits = salary * float(self.benefits_load_pct) / 100
        expected_hires = self.planned_headcount * float(self.attrition_rate_pct) / 100
        recruitment = expected_hires * float(self.cost_per_hire or 0)
        self.total_salary_cost = round(salary, 2)
        self.total_benefits_cost = round(benefits, 2)
        self.total_recruitment_cost = round(recruitment, 2)
        self.total_workforce_cost = round(
            salary + benefits + recruitment + float(self.contractor_spend or 0), 2
        )


class CostForecastLineItem(models.Model):
    """Year-by-year breakdown line for a workforce cost forecast."""

    COST_CATEGORY_CHOICES = [
        ('salary', 'Base Salary'),
        ('bonus', 'Bonus / Incentive'),
        ('benefits', 'Benefits'),
        ('recruitment', 'Recruitment'),
        ('training', 'Training & Development'),
        ('contractor', 'Contractor / Contingent'),
        ('severance', 'Severance'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='cost_forecast_line_items'
    )
    forecast = models.ForeignKey(
        WorkforceCostForecast, on_delete=models.CASCADE,
        related_name='line_items'
    )
    year = models.IntegerField()
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    cost_category = models.CharField(max_length=20, choices=COST_CATEGORY_CHOICES)
    headcount = models.IntegerField(default=0)
    budgeted_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    actual_amount = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'cost_forecast_line_items'
        ordering = ['year', 'cost_category']

    def __str__(self):
        return f"{self.forecast} | {self.year} | {self.cost_category}"

    @property
    def variance(self):
        if self.actual_amount is None:
            return None
        return round(float(self.budgeted_amount) - float(self.actual_amount), 2)


# ---------------------------------------------------------------------------
# 8. Department Budget vs Actual Headcount
# ---------------------------------------------------------------------------

class DepartmentBudgetActual(models.Model):
    """Monthly/quarterly department headcount budget vs actual tracking."""

    PERIOD_TYPE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='dept_budget_actuals'
    )
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.CASCADE,
        related_name='budget_actuals'
    )
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='budget_actuals'
    )
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES, default='monthly')
    period_year = models.IntegerField()
    period_number = models.IntegerField(
        help_text='Month (1-12) or quarter (1-4) or 0 for annual'
    )
    budgeted_headcount = models.IntegerField(default=0)
    actual_headcount = models.IntegerField(default=0)
    budgeted_cost = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    actual_cost = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    contractor_count = models.IntegerField(default=0)
    open_positions = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default='LKR')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'department_budget_actuals'
        unique_together = [['department', 'period_year', 'period_number', 'period_type']]
        ordering = ['-period_year', '-period_number']

    def __str__(self):
        return f"{self.department} | {self.period_year}/{self.period_number} ({self.period_type})"

    @property
    def headcount_variance(self):
        return self.actual_headcount - self.budgeted_headcount

    @property
    def cost_variance(self):
        if self.budgeted_cost is None or self.actual_cost is None:
            return None
        return round(float(self.actual_cost) - float(self.budgeted_cost), 2)


# ---------------------------------------------------------------------------
# 9. Location / Site Workforce Plan
# ---------------------------------------------------------------------------

class LocationWorkforcePlan(models.Model):
    """Workforce plan by office location / site."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='location_workforce_plans'
    )
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='location_plans'
    )
    location_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2, help_text='ISO 3166-1 alpha-2')
    plan_year = models.IntegerField()
    current_headcount = models.IntegerField(default=0)
    planned_headcount = models.IntegerField(default=0)
    fte_count = models.DecimalField(
        max_digits=7, decimal_places=2, default=0
    )
    contractor_count = models.IntegerField(default=0)
    remote_count = models.IntegerField(default=0)
    hybrid_count = models.IntegerField(default=0)
    onsite_count = models.IntegerField(default=0)
    office_capacity = models.IntegerField(
        null=True, blank=True, help_text='Physical desk / seat capacity'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'location_workforce_plans'
        unique_together = [['tenant', 'location_name', 'plan_year']]
        ordering = ['location_name']

    def __str__(self):
        return f"{self.location_name} ({self.country}) — {self.plan_year}"

    @property
    def utilisation_pct(self):
        if not self.office_capacity:
            return None
        return round(self.onsite_count / self.office_capacity * 100, 1)


# ---------------------------------------------------------------------------
# 10. Contractor vs FTE Mix Plan
# ---------------------------------------------------------------------------

class WorkforceMixPlan(models.Model):
    """Plan for contractor vs FTE workforce composition."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='workforce_mix_plans'
    )
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='mix_plans'
    )
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='mix_plans',
        help_text='Null = company-wide mix plan'
    )
    plan_year = models.IntegerField()
    # Targets
    target_fte_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=80.00,
        help_text='Target FTE as % of total workforce'
    )
    target_contractor_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00
    )
    target_intern_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00
    )
    # Actuals (computed / synced)
    actual_fte_count = models.IntegerField(default=0)
    actual_contractor_count = models.IntegerField(default=0)
    actual_intern_count = models.IntegerField(default=0)
    actual_total_count = models.IntegerField(default=0)
    # Cost comparison
    avg_fte_annual_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    avg_contractor_daily_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    rationale = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'workforce_mix_plans'
        unique_together = [['tenant', 'department', 'plan_year']]
        ordering = ['-plan_year']

    def __str__(self):
        dept = str(self.department) if self.department else 'Company-wide'
        return f"Mix Plan {self.plan_year} — {dept}"

    @property
    def actual_fte_pct(self):
        if not self.actual_total_count:
            return 0
        return round(self.actual_fte_count / self.actual_total_count * 100, 1)

    @property
    def actual_contractor_pct(self):
        if not self.actual_total_count:
            return 0
        return round(self.actual_contractor_count / self.actual_total_count * 100, 1)


# ---------------------------------------------------------------------------
# 11. Critical Role Mapping
# ---------------------------------------------------------------------------

class CriticalRoleMapping(models.Model):
    """Maps critical roles to their planning attributes and succession coverage."""

    IMPACT_LEVEL_CHOICES = [
        ('strategic', 'Strategic'),
        ('operational', 'Operational'),
        ('technical', 'Technical'),
    ]

    COVERAGE_STATUS_CHOICES = [
        ('covered', 'Covered'),
        ('at_risk', 'At Risk'),
        ('gap', 'Gap — No Successor'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='critical_role_mappings'
    )
    position = models.ForeignKey(
        'core_hr.Position', on_delete=models.CASCADE,
        related_name='critical_role_mappings'
    )
    critical_role_ref = models.ForeignKey(
        'core_hr.CriticalRole', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='planning_mappings'
    )
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='critical_role_mappings'
    )
    impact_level = models.CharField(
        max_length=15, choices=IMPACT_LEVEL_CHOICES, default='strategic'
    )
    time_to_fill_days = models.IntegerField(
        null=True, blank=True, help_text='Estimated days to fill if vacant'
    )
    revenue_risk = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True,
        help_text='Estimated revenue at risk if role is vacant'
    )
    currency = models.CharField(max_length=3, default='LKR')
    successor_count = models.IntegerField(default=0)
    coverage_status = models.CharField(
        max_length=15, choices=COVERAGE_STATUS_CHOICES, default='gap'
    )
    skills_gap_summary = models.TextField(blank=True)
    action_plan = models.TextField(blank=True)
    review_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'critical_role_mappings'
        ordering = ['impact_level', '-successor_count']

    def __str__(self):
        return f"Critical: {self.position} ({self.coverage_status})"


# ---------------------------------------------------------------------------
# 12. Succession Coverage Plan
# ---------------------------------------------------------------------------

class SuccessionCoveragePlan(models.Model):
    """Company-level succession coverage summary per plan period."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='succession_coverage_plans'
    )
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='succession_coverage_plans'
    )
    plan_year = models.IntegerField()
    company = models.ForeignKey(
        'core_hr.Company', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='succession_coverage_plans'
    )
    total_critical_roles = models.IntegerField(default=0)
    roles_with_successor = models.IntegerField(default=0)
    roles_ready_now = models.IntegerField(default=0)
    roles_ready_12m = models.IntegerField(default=0)
    roles_ready_24m = models.IntegerField(default=0)
    roles_no_successor = models.IntegerField(default=0)
    coverage_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='% of critical roles with at least one identified successor'
    )
    readiness_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Weighted readiness score 0-100'
    )
    notes = models.TextField(blank=True)
    computed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'succession_coverage_plans'
        unique_together = [['tenant', 'plan_year', 'company']]
        ordering = ['-plan_year']

    def __str__(self):
        return f"Succession Coverage {self.plan_year} — {self.coverage_pct}% covered"

    def recompute(self):
        """Recompute coverage_pct and readiness_score from raw counts."""
        if self.total_critical_roles == 0:
            self.coverage_pct = 0
            self.readiness_score = 0
            return
        self.coverage_pct = round(
            self.roles_with_successor / self.total_critical_roles * 100, 2
        )
        # Weighted: ready_now=1.0, ready_12m=0.75, ready_24m=0.5
        weighted = (
            self.roles_ready_now * 1.0
            + self.roles_ready_12m * 0.75
            + self.roles_ready_24m * 0.5
        )
        self.readiness_score = round(
            weighted / self.total_critical_roles * 100, 2
        )


# ---------------------------------------------------------------------------
# 13. Skills Demand Forecast
# ---------------------------------------------------------------------------

class SkillsDemandForecast(models.Model):
    """Forecast of skills demand by function / department over time."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('final', 'Final'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='skills_demand_forecasts'
    )
    name = models.CharField(max_length=200)
    forecast_year = models.IntegerField()
    horizon_years = models.IntegerField(default=3)
    company = models.ForeignKey(
        'core_hr.Company', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    linked_scenario = models.ForeignKey(
        WorkforceScenario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='skills_forecasts'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    methodology_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'skills_demand_forecasts'
        ordering = ['-forecast_year']

    def __str__(self):
        return f"{self.name} ({self.forecast_year})"


class SkillsDemandLineItem(models.Model):
    """Individual skill demand line item within a forecast."""

    DEMAND_TREND_CHOICES = [
        ('growing', 'Growing'),
        ('stable', 'Stable'),
        ('declining', 'Declining'),
        ('emerging', 'Emerging'),
        ('critical_shortage', 'Critical Shortage'),
    ]

    GAP_STRATEGY_CHOICES = [
        ('hire', 'Hire Externally'),
        ('upskill', 'Upskill Existing'),
        ('reskill', 'Reskill from Other Functions'),
        ('contract', 'Use Contractors'),
        ('automate', 'Automate / AI'),
        ('partner', 'Outsource / Partner'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='skills_demand_line_items'
    )
    forecast = models.ForeignKey(
        SkillsDemandForecast, on_delete=models.CASCADE,
        related_name='line_items'
    )
    year = models.IntegerField()
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    skill_name = models.CharField(max_length=200)
    skill_category = models.CharField(max_length=100, blank=True)
    current_proficient_count = models.IntegerField(
        default=0, help_text='Employees currently proficient in this skill'
    )
    required_count = models.IntegerField(
        help_text='Required proficient employees by target year'
    )
    gap_count = models.IntegerField(
        default=0, help_text='Required minus current (computed)'
    )
    demand_trend = models.CharField(
        max_length=20, choices=DEMAND_TREND_CHOICES, default='growing'
    )
    gap_strategy = models.CharField(
        max_length=20, choices=GAP_STRATEGY_CHOICES, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'skills_demand_line_items'
        ordering = ['year', 'skill_name']

    def __str__(self):
        return f"{self.forecast} | {self.year} | {self.skill_name} (gap: {self.gap_count})"

    def save(self, *args, **kwargs):
        self.gap_count = max(0, self.required_count - self.current_proficient_count)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 14. Hiring Requisition  (with TalentOS handoff fields)
# ---------------------------------------------------------------------------

class HiringRequisition(models.Model):
    """Approved hiring request with handoff to TalentOS / ATS."""

    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
    ]

    REASON_CHOICES = [
        ('new_headcount', 'New Headcount'),
        ('backfill', 'Backfill'),
        ('internal_transfer', 'Internal Transfer'),
        ('temp_to_perm', 'Temp to Perm'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # TalentOS handoff status
    TALENTOSS_SYNC_STATUS = [
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent to TalentOS'),
        ('synced', 'Synced'),
        ('error', 'Sync Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='hiring_requisitions'
    )
    requisition_number = models.CharField(max_length=30, unique=True)
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='requisitions'
    )
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.CASCADE,
        related_name='hiring_requisitions'
    )
    position = models.ForeignKey(
        'core_hr.Position', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='hiring_requisitions'
    )
    title = models.CharField(max_length=300)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    target_start_date = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    budget_grade = models.CharField(max_length=50, blank=True)
    salary_range_min = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    salary_range_max = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    hiring_manager = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_requisitions'
    )
    required_skills = models.JSONField(
        default=list, help_text='List of required skill strings'
    )
    job_description = models.TextField(blank=True)
    # TalentOS handoff
    talentoss_job_id = models.CharField(
        max_length=100, blank=True,
        help_text='Job ID in TalentOS / ATS once synced'
    )
    talentoss_sync_status = models.CharField(
        max_length=10, choices=TALENTOSS_SYNC_STATUS, default='not_sent'
    )
    talentoss_synced_at = models.DateTimeField(null=True, blank=True)
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_requisitions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    filled_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'hiring_requisitions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.requisition_number} — {self.title}"


# ---------------------------------------------------------------------------
# 15. Reorg / Change-Management Workflow
# ---------------------------------------------------------------------------

class ReorgWorkflow(models.Model):
    """Manages the change-management workflow for an org restructure."""

    REORG_TYPE_CHOICES = [
        ('full_reorg', 'Full Reorganisation'),
        ('department_split', 'Department Split'),
        ('department_merge', 'Department Merge'),
        ('leadership_change', 'Leadership Change'),
        ('location_closure', 'Location Closure'),
        ('function_outsource', 'Function Outsource'),
        ('rif', 'Reduction in Force (RIF)'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('impact_assessment', 'Impact Assessment'),
        ('executive_review', 'Executive Review'),
        ('approved', 'Approved'),
        ('communication', 'Communication Phase'),
        ('implementation', 'Implementation'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='reorg_workflows'
    )
    name = models.CharField(max_length=300)
    reorg_type = models.CharField(max_length=25, choices=REORG_TYPE_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='planning')
    org_scenario = models.ForeignKey(
        OrgDesignScenario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reorg_workflows'
    )
    workforce_scenario = models.ForeignKey(
        WorkforceScenario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reorg_workflows'
    )
    # Key dates
    announced_date = models.DateField(null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    # Impact
    employees_impacted = models.IntegerField(default=0)
    roles_eliminated = models.IntegerField(default=0)
    roles_created = models.IntegerField(default=0)
    net_headcount_change = models.IntegerField(default=0)
    estimated_cost_impact = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default='LKR')
    # Ownership
    executive_sponsor = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sponsored_reorgs'
    )
    hr_lead = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='led_reorgs'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'reorg_workflows'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.reorg_type}, {self.status})"


class ReorgWorkflowTask(models.Model):
    """Individual task / milestone within a reorg workflow."""

    TASK_TYPE_CHOICES = [
        ('legal_review', 'Legal Review'),
        ('hr_impact_analysis', 'HR Impact Analysis'),
        ('finance_sign_off', 'Finance Sign-off'),
        ('executive_approval', 'Executive Approval'),
        ('board_approval', 'Board Approval'),
        ('communication_plan', 'Communication Plan'),
        ('employee_notification', 'Employee Notification'),
        ('manager_briefing', 'Manager Briefing'),
        ('systems_update', 'Systems Update (HRIS)'),
        ('payroll_update', 'Payroll Update'),
        ('benefits_transition', 'Benefits Transition'),
        ('knowledge_transfer', 'Knowledge Transfer'),
        ('offboarding', 'Offboarding'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('blocked', 'Blocked'),
        ('waived', 'Waived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='reorg_workflow_tasks'
    )
    workflow = models.ForeignKey(
        ReorgWorkflow, on_delete=models.CASCADE,
        related_name='tasks'
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reorg_tasks'
    )
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    sequence = models.IntegerField(default=0)
    is_mandatory = models.BooleanField(default=True)
    blockers = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'workforce_planning'
        db_table = 'reorg_workflow_tasks'
        ordering = ['sequence', 'due_date']

    def __str__(self):
        return f"{self.workflow} | {self.title} ({self.status})"
