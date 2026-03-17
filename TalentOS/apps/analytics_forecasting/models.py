"""Analytics Forecasting app — Predictive pipeline analytics, capacity planning, and fairness reporting."""

import uuid
from django.db import models


class FillTimeForecast(models.Model):
    """ML-generated forecast of how long a job will take to fill."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="fill_time_forecasts")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="fill_time_forecasts")
    predicted_days_to_fill = models.FloatField()
    confidence_interval_low = models.FloatField(null=True, blank=True)
    confidence_interval_high = models.FloatField(null=True, blank=True)
    model_version = models.CharField(max_length=50, blank=True, default="")
    feature_importances = models.JSONField(
        default=dict, blank=True,
        help_text="EU AI Act Annex III — explainability: feature weights used in prediction"
    )
    forecast_date = models.DateField(auto_now_add=True)
    actual_days_to_fill = models.FloatField(null=True, blank=True, help_text="Populated when job closes")
    human_reviewed = models.BooleanField(default=False)

    class Meta:
        db_table = "fill_time_forecasts"
        ordering = ["-forecast_date"]
        indexes = [
            models.Index(fields=["tenant", "job"]),
        ]

    def __str__(self):
        return f"Fill forecast: {self.job.title} → {self.predicted_days_to_fill:.0f}d"


class RecruiterCapacityPlan(models.Model):
    """Planned vs actual recruiter workload for a given period."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="recruiter_capacity_plans")
    recruiter = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="capacity_plans"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    planned_open_roles = models.IntegerField(default=0)
    actual_open_roles = models.IntegerField(default=0)
    planned_hires = models.IntegerField(default=0)
    actual_hires = models.IntegerField(default=0)
    capacity_utilisation_pct = models.FloatField(
        null=True, blank=True, help_text="Actual / planned * 100"
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recruiter_capacity_plans"
        ordering = ["-period_start"]
        unique_together = [("tenant", "recruiter", "period_start")]

    def __str__(self):
        return f"Capacity: {self.recruiter_id} {self.period_start}–{self.period_end}"


class InterviewerLoadForecast(models.Model):
    """Forecasted interviewer scheduling load for upcoming weeks."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="interviewer_load_forecasts"
    )
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="load_forecasts"
    )
    week_start = models.DateField()
    predicted_interview_count = models.IntegerField(default=0)
    predicted_hours = models.FloatField(default=0.0)
    capacity_hours = models.FloatField(default=10.0, help_text="Hours available for interviews per week")
    overloaded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interviewer_load_forecasts"
        ordering = ["week_start"]
        unique_together = [("tenant", "interviewer", "week_start")]

    def __str__(self):
        return f"Load forecast: {self.interviewer_id} w/c {self.week_start}"


class CloseRateForecast(models.Model):
    """Predicted close rate (offer acceptance probability) for an offer."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="close_rate_forecasts")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="close_rate_forecasts"
    )
    predicted_acceptance_probability = models.FloatField(help_text="0–1 probability")
    key_factors = models.JSONField(
        default=list, blank=True,
        help_text="EU AI Act Annex III — top factors influencing prediction"
    )
    model_version = models.CharField(max_length=50, blank=True, default="")
    forecast_date = models.DateField(auto_now_add=True)
    actual_outcome = models.CharField(
        max_length=20, blank=True, default="",
        help_text="accepted/declined — populated after outcome known"
    )

    class Meta:
        db_table = "close_rate_forecasts"
        ordering = ["-forecast_date"]

    def __str__(self):
        return f"Close rate: {self.application_id} → {self.predicted_acceptance_probability:.0%}"


class FairnessReport(models.Model):
    """Statistical fairness / equity report across a hiring funnel segment."""

    REPORT_TYPE_CHOICES = [
        ("gender", "Gender Parity"),
        ("ethnicity", "Ethnic Diversity"),
        ("age", "Age Equity"),
        ("disability", "Disability Inclusion"),
        ("combined", "Combined Equity"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="fairness_reports")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fairness_reports",
        help_text="Null = tenant-wide report"
    )
    funnel_data = models.JSONField(
        default=dict, blank=True,
        help_text='{"applied": {"female": 120, "male": 180}, "hired": {...}}'
    )
    adverse_impact_flags = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fairness_reports_reviewed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fairness_reports"
        ordering = ["-period_start"]

    def __str__(self):
        return f"Fairness ({self.report_type}) {self.period_start}–{self.period_end}"


class PipelineBottleneck(models.Model):
    """Detected bottleneck in a hiring pipeline stage."""

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="pipeline_bottlenecks")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, null=True, blank=True,
        related_name="bottlenecks"
    )
    stage_name = models.CharField(max_length=100)
    avg_days_in_stage = models.FloatField()
    benchmark_days = models.FloatField(help_text="Expected / target days in stage")
    candidates_stuck = models.IntegerField(default=0)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    suggested_action = models.TextField(blank=True, default="")
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pipeline_bottlenecks"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"Bottleneck: {self.stage_name} ({self.severity})"


class ProcessAlert(models.Model):
    """A system-generated alert about a recruiting process anomaly or SLA breach."""

    ALERT_TYPE_CHOICES = [
        ("sla_breach", "SLA Breach"),
        ("idle_candidates", "Idle Candidates"),
        ("low_pipeline", "Low Pipeline Volume"),
        ("high_drop_off", "High Drop-off Rate"),
        ("bias_signal", "Bias Signal Detected"),
        ("vendor_sla_breach", "Vendor SLA Breach"),
        ("interviewer_overload", "Interviewer Overload"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="process_alerts")
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    detail = models.TextField(blank=True, default="")
    related_job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="process_alerts"
    )
    severity = models.CharField(max_length=20, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_process_alerts"
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "process_alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "alert_type"]),
        ]

    def __str__(self):
        return f"Alert: {self.title} ({self.status})"
