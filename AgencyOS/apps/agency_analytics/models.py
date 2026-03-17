"""
Agency Analytics models.
Stores aggregated KPI snapshots, funnel metrics, desk performance,
recruiter productivity, client profitability, and forecasting data.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DailyKPISnapshot(models.Model):
    """
    Daily aggregated KPI snapshot for an agency.
    Pre-computed to enable fast dashboard queries.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="kpi_snapshots"
    )
    snapshot_date = models.DateField()
    # Pipeline
    open_job_orders = models.IntegerField(default=0)
    active_assignments = models.IntegerField(default=0)
    total_submissions = models.IntegerField(default=0)
    new_submissions = models.IntegerField(default=0)
    # Funnel
    submissions_to_interviews = models.IntegerField(default=0)
    interviews_to_offers = models.IntegerField(default=0)
    offers_to_starts = models.IntegerField(default=0)
    placements_this_day = models.IntegerField(default=0)
    # Financial
    revenue_this_day = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_margin_this_day = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    # Contractors
    contractors_available = models.IntegerField(default=0)
    contractors_on_assignment = models.IntegerField(default=0)
    assignments_ending_in_30_days = models.IntegerField(default=0)
    # Compliance
    expiring_credentials_30d = models.IntegerField(default=0)
    open_compliance_issues = models.IntegerField(default=0)
    # Timesheets
    timesheets_pending_approval = models.IntegerField(default=0)
    timesheets_missing = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_daily_kpi"
        unique_together = [["agency", "snapshot_date"]]
        ordering = ["-snapshot_date"]

    def __str__(self):
        return f"KPI {self.agency.name} – {self.snapshot_date}"


class RecruiterPerformance(models.Model):
    """
    Period-level performance snapshot for a recruiter.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="recruiter_performance"
    )
    recruiter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="performance_records"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    # Activity
    calls_made = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    candidates_sourced = models.IntegerField(default=0)
    submissions_made = models.IntegerField(default=0)
    interviews_arranged = models.IntegerField(default=0)
    placements_made = models.IntegerField(default=0)
    # Financial
    currency = models.CharField(max_length=10, default="USD")
    revenue_generated = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_margin_generated = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission_earned = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Rates
    submission_to_interview_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    interview_to_offer_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    offer_to_start_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_recruiter_perf"
        unique_together = [["agency", "recruiter", "period_start"]]
        ordering = ["-period_start"]

    def __str__(self):
        return f"Perf: {self.recruiter.get_full_name()} – {self.period_start}"


class ClientAnalytics(models.Model):
    """
    Period-level analytics for a client account.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="client_analytics"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount",
        on_delete=models.CASCADE,
        related_name="analytics_records",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    # Metrics
    job_orders_received = models.IntegerField(default=0)
    job_orders_filled = models.IntegerField(default=0)
    fill_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_time_to_fill_days = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    avg_time_to_submit_days = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    submissions_sent = models.IntegerField(default=0)
    interviews_conducted = models.IntegerField(default=0)
    offers_made = models.IntegerField(default=0)
    placements_made = models.IntegerField(default=0)
    contractors_active = models.IntegerField(default=0)
    # Financial
    currency = models.CharField(max_length=10, default="USD")
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_margin = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    invoices_outstanding = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    dso_days = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_client"
        unique_together = [["agency", "client_account", "period_start"]]
        ordering = ["-period_start"]

    def __str__(self):
        return f"Client Analytics: {self.client_account} – {self.period_start}"


class FunnelMetrics(models.Model):
    """
    Agency-wide funnel conversion metrics by period.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="funnel_metrics"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    # Funnel stages
    sourced = models.IntegerField(default=0)
    screened = models.IntegerField(default=0)
    submitted = models.IntegerField(default=0)
    shortlisted = models.IntegerField(default=0)
    interviewed = models.IntegerField(default=0)
    offered = models.IntegerField(default=0)
    placed = models.IntegerField(default=0)
    # Rates
    source_to_submit_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    submit_to_interview_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    interview_to_offer_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    offer_to_start_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    # Churn signals
    ghosting_count = models.IntegerField(default=0)
    withdrawal_count = models.IntegerField(default=0)
    rejection_count = models.IntegerField(default=0)
    fallthrough_count = models.IntegerField(default=0)
    redeployment_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_funnel"
        unique_together = [["agency", "period_start"]]
        ordering = ["-period_start"]

    def __str__(self):
        return f"Funnel: {self.agency.name} – {self.period_start}"
