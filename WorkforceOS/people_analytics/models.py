"""
People Analytics models — attrition risk, headcount snapshots,
turnover reports, diversity metrics, and saved reports.
"""

import uuid
from django.db import models
from django.conf import settings


class AttritionRiskScore(models.Model):
    """Computed attrition risk score per employee."""

    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='attrition_risk_scores'
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE,
        related_name='attrition_risk_scores'
    )
    computed_date = models.DateField()
    risk_score = models.IntegerField(help_text='0–100')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES)
    contributing_factors = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    model_version = models.CharField(max_length=20)
    is_current = models.BooleanField(default=True)

    class Meta:
        app_label = 'people_analytics'
        db_table = 'attrition_risk_scores'
        ordering = ['-computed_date']
        unique_together = [['employee', 'computed_date']]

    def __str__(self):
        return f"{self.employee} — {self.risk_level} ({self.computed_date})"


class HeadcountSnapshot(models.Model):
    """Monthly headcount snapshot by department."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='headcount_snapshots'
    )
    snapshot_date = models.DateField()
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='headcount_snapshots'
    )
    company = models.ForeignKey(
        'core_hr.Company', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='headcount_snapshots'
    )
    headcount = models.IntegerField()
    new_hires = models.IntegerField(default=0)
    terminations = models.IntegerField(default=0)
    transfers_in = models.IntegerField(default=0)
    transfers_out = models.IntegerField(default=0)
    avg_tenure_months = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    avg_salary = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    gender_breakdown = models.JSONField(default=dict)
    employment_type_breakdown = models.JSONField(default=dict)

    class Meta:
        app_label = 'people_analytics'
        db_table = 'headcount_snapshots'
        ordering = ['-snapshot_date']

    def __str__(self):
        dept = self.department.name if self.department else 'All'
        return f"Snapshot {self.snapshot_date} — {dept}"


class TurnoverReport(models.Model):
    """Computed turnover metrics per period."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='turnover_reports'
    )
    period_year = models.IntegerField()
    period_month = models.IntegerField(null=True, blank=True)
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='turnover_reports'
    )
    headcount_start = models.IntegerField()
    headcount_end = models.IntegerField()
    voluntary_exits = models.IntegerField(default=0)
    involuntary_exits = models.IntegerField(default=0)
    total_exits = models.IntegerField(default=0)
    turnover_rate = models.DecimalField(max_digits=6, decimal_places=3)
    regrettable_exits = models.IntegerField(default=0)
    avg_tenure_at_exit_months = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    top_exit_reasons = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'people_analytics'
        db_table = 'turnover_reports'
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        period = f"{self.period_year}-{self.period_month:02d}" if self.period_month else str(self.period_year)
        return f"Turnover {period}"


class DiversityMetric(models.Model):
    """DEI metric snapshot."""

    METRIC_TYPE_CHOICES = [
        ('gender', 'Gender'),
        ('age', 'Age'),
        ('tenure', 'Tenure'),
        ('nationality', 'Nationality'),
        ('employment_type', 'Employment Type'),
        ('department_distribution', 'Department Distribution'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='diversity_metrics'
    )
    metric_date = models.DateField()
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPE_CHOICES)
    scope_department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='diversity_metrics'
    )
    data = models.JSONField(default=dict, help_text='Full breakdown dict')
    total_count = models.IntegerField()
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'people_analytics'
        db_table = 'diversity_metrics'
        ordering = ['-metric_date']

    def __str__(self):
        return f"{self.metric_type} — {self.metric_date}"


class PeopleAnalyticsReport(models.Model):
    """Saved / scheduled analytics report."""

    REPORT_TYPE_CHOICES = [
        ('headcount', 'Headcount'),
        ('turnover', 'Turnover'),
        ('diversity', 'Diversity'),
        ('pay_equity', 'Pay Equity'),
        ('engagement', 'Engagement'),
        ('performance', 'Performance'),
        ('custom', 'Custom'),
    ]

    SCHEDULE_CHOICES = [
        ('manual', 'Manual'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    OUTPUT_FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('pdf', 'PDF'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='people_analytics_reports'
    )
    name = models.CharField(max_length=300)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    schedule = models.CharField(max_length=10, choices=SCHEDULE_CHOICES, default='manual')
    config = models.JSONField(
        default=dict,
        help_text='Filters, groupings, metrics configuration'
    )
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_result = models.JSONField(null=True, blank=True)
    output_format = models.CharField(max_length=10, choices=OUTPUT_FORMAT_CHOICES, default='json')
    recipients = models.JSONField(default=list, help_text='List of user UUIDs')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_analytics_reports'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'people_analytics'
        db_table = 'people_analytics_reports'
        ordering = ['name']

    def __str__(self):
        return self.name
