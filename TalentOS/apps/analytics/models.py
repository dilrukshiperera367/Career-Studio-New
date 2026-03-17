"""Analytics app — Materialized metrics for dashboard performance."""

import uuid
from django.db import models


class AnalyticsDaily(models.Model):
    """Pre-computed daily metrics per job per tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="analytics")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, null=True, blank=True, related_name="analytics"
    )
    metric = models.CharField(max_length=50, db_index=True)
    value = models.FloatField()
    metadata = models.JSONField(default=dict, blank=True)
    computed_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_daily"
        unique_together = [("tenant", "job", "metric", "computed_date")]
        indexes = [
            models.Index(fields=["tenant", "computed_date"]),
            models.Index(fields=["tenant", "metric", "computed_date"]),
        ]

    def __str__(self):
        return f"{self.metric}: {self.value} ({self.computed_date})"


class SavedReport(models.Model):
    """Custom report definition with optional scheduled delivery."""

    SCHEDULE_CHOICES = [
        ("none", "No Schedule"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="saved_reports")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    report_type = models.CharField(max_length=50,
        help_text="pipeline_funnel, source_roi, recruiter_performance, time_to_hire, diversity, custom")
    query_config = models.JSONField(default=dict, blank=True,
        help_text='{"fields": [...], "filters": {...}, "group_by": "...", "date_range": "..."}')
    schedule = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default="none")
    recipients = models.JSONField(default=list, blank=True,
        help_text='["user_id_1", "user_id_2"] or ["email@example.com"]')
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_reports"

    def __str__(self):
        return f"Report: {self.name}"
