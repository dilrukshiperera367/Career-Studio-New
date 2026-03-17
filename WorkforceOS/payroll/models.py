"""
Payroll models — Salary structures, payroll runs, entries,
statutory rules, loans, and payroll audit.
"""

import uuid
from django.db import models
from django.conf import settings


# ============ SALARY STRUCTURES ============

class SalaryStructure(models.Model):
    """Template defining earning and deduction components."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='salary_structures')
    company = models.ForeignKey('core_hr.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='salary_structures')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    components = models.JSONField(default=list, help_text='[{"name":"...", "type":"earning|deduction", "calc_type":"fixed|percentage|formula", "value": 0, "basis":"basic|gross"}]')
    applicable_grades = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'salary_structures'

    def __str__(self):
        return self.name


# ============ EMPLOYEE COMPENSATION ============

class EmployeeCompensation(models.Model):
    """Individual employee salary assignment (current + history)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='employee_compensations')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='compensations')
    salary_structure = models.ForeignKey(SalaryStructure, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    effective_date = models.DateField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    components = models.JSONField(default=list, blank=True, help_text='Per-employee overrides')
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='LKR')
    payment_frequency = models.CharField(max_length=20, default='monthly', choices=[
        ('monthly', 'Monthly'), ('bi_weekly', 'Bi-weekly'), ('weekly', 'Weekly'),
    ])
    bank_details = models.JSONField(default=dict, blank=True)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'employee_compensations'
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['employee', '-effective_date'], name='idx_comp_emp_date'),
        ]

    def __str__(self):
        return f"{self.employee} — {self.basic_salary} {self.currency} (from {self.effective_date})"


# ============ PAYROLL RUNS ============

class PayrollRun(models.Model):
    """Monthly payroll processing batch."""
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('processing', 'Processing'), ('review', 'Review'),
        ('approved', 'Approved'), ('finalized', 'Finalized'), ('reversed', 'Reversed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='payroll_runs')
    company = models.ForeignKey('core_hr.Company', on_delete=models.CASCADE, related_name='payroll_runs')
    period_year = models.IntegerField()
    period_month = models.IntegerField()
    name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='draft', choices=STATUS_CHOICES)
    employee_count = models.IntegerField(default=0)
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_employer_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    finalized_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_runs'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'company', 'period_year', 'period_month'], name='unique_payroll_period')
        ]

    def __str__(self):
        return f"Payroll {self.period_year}-{self.period_month:02d} ({self.company.name})"


# ============ PAYROLL ENTRIES ============

class PayrollEntry(models.Model):
    """Per-employee payroll calculation result within a payroll run."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='payroll_entries')
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='entries')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='payroll_entries')

    # Earnings
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    earnings_json = models.JSONField(default=list, help_text='[{"component": "...", "amount": 0, "description": "..."}]')
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Deductions
    deductions_json = models.JSONField(default=list)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Statutory (Sri Lanka)
    epf_employee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="8% of relevant earnings")
    epf_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="12% of relevant earnings")
    etf_employer = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="3% of relevant earnings")
    apit = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Advanced Personal Income Tax")
    statutory_json = models.JSONField(default=dict, blank=True)

    # OT & Attendance
    ot_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ot_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    days_worked = models.IntegerField(null=True, blank=True)
    days_absent = models.IntegerField(default=0)

    # Loan deductions
    loan_deductions = models.JSONField(default=list, help_text='[{"loan_id": "...", "amount": 0, "remaining": 0}]')

    # Totals
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employer_total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment
    payment_method = models.CharField(max_length=20, default='bank', choices=[
        ('bank', 'Bank Transfer'), ('cash', 'Cash'), ('cheque', 'Cheque'),
    ])
    bank_details = models.JSONField(default=dict, blank=True)

    # Payslip
    payslip_url = models.URLField(max_length=500, blank=True)
    payslip_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_entries'
        constraints = [
            models.UniqueConstraint(fields=['payroll_run', 'employee'], name='unique_payroll_entry')
        ]
        indexes = [
            models.Index(fields=['tenant', 'employee'], name='idx_payentry_emp'),
        ]

    def __str__(self):
        return f"{self.employee} — Net: {self.net_salary}"


# ============ STATUTORY RULES (Plugin Model) ============

class StatutoryRule(models.Model):
    """Country-specific tax/contribution rules. Pluggable per country."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.CharField(max_length=3)
    rule_type = models.CharField(max_length=50, choices=[
        ('epf_employee', 'EPF Employee'), ('epf_employer', 'EPF Employer'),
        ('etf', 'ETF'), ('income_tax', 'Income Tax'), ('gratuity', 'Gratuity'),
    ])
    name = models.CharField(max_length=100)
    calculation = models.JSONField(help_text='{"type": "percentage|slab", "rate": 0.08, "slabs": [{"from":0, "to":..., "rate":...}]}')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'statutory_rules'
        ordering = ['country', 'rule_type', '-effective_from']
        indexes = [
            models.Index(fields=['country', 'rule_type', 'effective_from'], name='idx_statutory_country'),
        ]

    def __str__(self):
        return f"{self.country}:{self.rule_type} — {self.name}"


# ============ LOAN RECORDS ============

class LoanRecord(models.Model):
    """Employee loan/advance with installment tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='loan_records')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='loans')
    loan_type = models.CharField(max_length=50, choices=[
        ('salary_advance', 'Salary Advance'), ('personal_loan', 'Personal Loan'),
        ('festival_advance', 'Festival Advance'), ('other', 'Other'),
    ])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    installments_total = models.IntegerField()
    installments_paid = models.IntegerField(default=0)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    start_date = models.DateField()
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('completed', 'Completed'), ('written_off', 'Written Off'),
    ])
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loan_records'

    def __str__(self):
        return f"{self.employee} — {self.loan_type}: {self.outstanding_balance} remaining"


# ============ PAYROLL AUDIT LOG ============

class PayrollAuditLog(models.Model):
    """Immutable audit log for payroll operations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='payroll_audit_logs')
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payroll_run', 'created_at'], name='idx_payaudit_run'),
        ]


# ============ FEATURE 5: PAYROLL & COMPENSATION PLANNING UPGRADES ============

class OffCycleCompChange(models.Model):
    """Off-cycle compensation change request outside normal merit cycle."""
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'), ('rejected', 'Rejected'), ('applied', 'Applied'),
    ]
    CHANGE_TYPES = [
        ('promotion', 'Promotion'), ('retention', 'Retention'),
        ('market_adjustment', 'Market Adjustment'), ('correction', 'Correction'), ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='off_cycle_comp_changes')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='off_cycle_comp_changes')
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPES)
    current_salary = models.DecimalField(max_digits=14, decimal_places=2)
    proposed_salary = models.DecimalField(max_digits=14, decimal_places=2)
    effective_date = models.DateField()
    justification = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'off_cycle_comp_changes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} — {self.change_type} ({self.status})"


class RetroPayEntry(models.Model):
    """Retroactive pay adjustment for backdated salary changes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='retro_pay_entries')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='retro_pay_entries')
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='retro_entries')
    retro_period_start = models.DateField()
    retro_period_end = models.DateField()
    old_salary = models.DecimalField(max_digits=14, decimal_places=2)
    new_salary = models.DecimalField(max_digits=14, decimal_places=2)
    retro_amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField(blank=True)
    is_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'retro_pay_entries'
        ordering = ['-retro_period_start']

    def __str__(self):
        return f"Retro {self.employee} — {self.retro_amount} ({self.retro_period_start} to {self.retro_period_end})"


class PayrollAnomaly(models.Model):
    """Auto-detected anomaly in payroll data (outlier, missing record, etc.)."""
    SEVERITY_CHOICES = [
        ('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical'),
    ]
    ANOMALY_TYPES = [
        ('large_variance', 'Large Salary Variance'), ('missing_record', 'Missing Record'),
        ('duplicate', 'Duplicate Entry'), ('statutory_mismatch', 'Statutory Mismatch'),
        ('negative_net', 'Negative Net Pay'), ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='payroll_anomalies')
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, null=True, blank=True, related_name='anomalies')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_anomalies')
    anomaly_type = models.CharField(max_length=30, choices=ANOMALY_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='warning')
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payroll_anomalies'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.anomaly_type} [{self.severity}] — {self.description[:60]}"


class PayCompressionAlert(models.Model):
    """Alert when a subordinate's pay approaches or exceeds their manager's."""
    ALERT_STATUSES = [
        ('open', 'Open'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='pay_compression_alerts')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='pay_compression_alerts')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='compression_alerts_as_manager')
    employee_salary = models.DecimalField(max_digits=14, decimal_places=2)
    manager_salary = models.DecimalField(max_digits=14, decimal_places=2)
    compression_ratio = models.DecimalField(max_digits=5, decimal_places=4, help_text='employee/manager salary ratio')
    threshold_used = models.DecimalField(max_digits=5, decimal_places=4, default=0.9)
    status = models.CharField(max_length=20, choices=ALERT_STATUSES, default='open')
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    notes = models.TextField(blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pay_compression_alerts'
        ordering = ['-detected_at']

    def __str__(self):
        return f"Compression: {self.employee} vs {self.manager} ({self.compression_ratio:.2%})"


class CompBenchmarkImport(models.Model):
    """Imported market compensation benchmark data (e.g., Mercer, Radford)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='comp_benchmark_imports')
    source = models.CharField(max_length=100, help_text='e.g. Mercer, Radford, Willis Towers Watson')
    survey_year = models.IntegerField()
    job_family = models.CharField(max_length=100, blank=True)
    job_level = models.CharField(max_length=50, blank=True)
    geography = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=3, default='LKR')
    p25 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    p50 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    p75 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    p90 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comp_benchmark_imports'
        ordering = ['-survey_year', 'job_family']

    def __str__(self):
        return f"{self.source} {self.survey_year} — {self.job_family} {self.job_level}"


class SalaryProgression(models.Model):
    """Historical salary progression timeline for an employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='salary_progressions')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='salary_progressions')
    effective_date = models.DateField()
    salary = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='LKR')
    change_reason = models.CharField(max_length=100, blank=True)
    change_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    compa_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'salary_progressions'
        ordering = ['employee', '-effective_date']

    def __str__(self):
        return f"{self.employee} — {self.salary} {self.currency} from {self.effective_date}"


class RewardSimulation(models.Model):
    """What-if simulation for compensation changes (merit/promo scenarios)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='reward_simulations')
    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    scope = models.JSONField(default=dict, help_text='{"department": "...", "grade": "...", "employee_ids": [...]}')
    scenario = models.JSONField(default=dict, help_text='{"merit_pct": 0.04, "promo_pct": 0.08, "flat_increase": 0}')
    results = models.JSONField(default=dict, blank=True, help_text='Computed cost impact and headcount breakdown')
    total_cost_impact = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    headcount_affected = models.IntegerField(default=0)
    is_finalized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reward_simulations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Simulation: {self.name} ({self.headcount_affected} employees)"


class BudgetGuardrail(models.Model):
    """Budget ceiling/floor guardrails for compensation planning cycles."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='budget_guardrails')
    name = models.CharField(max_length=200)
    cycle_year = models.IntegerField()
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_guardrails')
    budget_type = models.CharField(max_length=30, choices=[
        ('merit_pool', 'Merit Pool'), ('bonus_pool', 'Bonus Pool'), ('total_comp', 'Total Comp'),
    ])
    budget_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    budget_pct_of_payroll = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    max_individual_increase_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'budget_guardrails'
        ordering = ['-cycle_year', 'name']

    def __str__(self):
        return f"{self.name} ({self.cycle_year}) — {self.budget_type}"


class VariablePayPlan(models.Model):
    """Variable pay / incentive plan definition (bonus scheme, commission, etc.)."""
    PLAN_TYPES = [
        ('bonus', 'Annual Bonus'), ('commission', 'Commission'), ('spot_bonus', 'Spot Bonus'),
        ('project_incentive', 'Project Incentive'), ('referral', 'Referral Bonus'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='variable_pay_plans')
    name = models.CharField(max_length=200)
    plan_type = models.CharField(max_length=30, choices=PLAN_TYPES)
    eligibility_criteria = models.JSONField(default=dict, help_text='{"grades": [...], "departments": [...], "min_tenure_months": 6}')
    calculation_rules = models.JSONField(default=dict, help_text='{"type":"percentage_of_salary", "rate":0.10, "performance_multipliers":{...}}')
    plan_year = models.IntegerField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'variable_pay_plans'
        ordering = ['-plan_year', 'name']

    def __str__(self):
        return f"{self.name} ({self.plan_type}, {self.plan_year})"


class VariablePayEntry(models.Model):
    """Individual variable pay award for an employee under a specific plan."""
    STATUS_CHOICES = [
        ('calculated', 'Calculated'), ('approved', 'Approved'),
        ('paid', 'Paid'), ('withheld', 'Withheld'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='variable_pay_entries')
    plan = models.ForeignKey(VariablePayPlan, on_delete=models.CASCADE, related_name='entries')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='variable_pay_entries')
    award_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='LKR')
    performance_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    multiplier_applied = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    calculation_breakdown = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='calculated')
    paid_in_run = models.ForeignKey(PayrollRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='variable_pay_entries')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'variable_pay_entries'
        ordering = ['-created_at']
        unique_together = ['plan', 'employee']

    def __str__(self):
        return f"{self.employee} — {self.plan.name}: {self.award_amount} ({self.status})"
