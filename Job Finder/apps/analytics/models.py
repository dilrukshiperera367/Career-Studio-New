"""Analytics app — Search logs, platform stats, event tracking."""
import uuid
from django.db import models
from django.conf import settings


class SearchLog(models.Model):
    """Logs every search performed on the platform for analytics & improvement."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=64, blank=True, default="")
    query = models.CharField(max_length=500)
    filters = models.JSONField(default=dict, blank=True)
    results_count = models.IntegerField(default=0)
    clicked_job_id = models.UUIDField(null=True, blank=True)
    clicked_position = models.IntegerField(null=True, blank=True)
    language = models.CharField(max_length=2, default="en")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_search_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="idx_search_log_date"),
        ]


class PlatformStat(models.Model):
    """Daily aggregated platform statistics."""
    date = models.DateField(primary_key=True)
    total_users = models.IntegerField(default=0)
    total_seekers = models.IntegerField(default=0)
    total_employers = models.IntegerField(default=0)
    total_jobs = models.IntegerField(default=0)
    active_jobs = models.IntegerField(default=0)
    total_applications = models.IntegerField(default=0)
    new_users_today = models.IntegerField(default=0)
    new_jobs_today = models.IntegerField(default=0)
    new_applications_today = models.IntegerField(default=0)
    searches_today = models.IntegerField(default=0)
    page_views_today = models.IntegerField(default=0)
    unique_visitors_today = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_platform_stats"
        ordering = ["-date"]


class EventLog(models.Model):
    """Generic event tracking for user actions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50)
    event_data = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_event_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "-created_at"], name="idx_event_type_date"),
        ]


class EmployerAnalytics(models.Model):
    """Per-employer daily analytics snapshot."""
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="analytics")
    date = models.DateField()
    job_views = models.IntegerField(default=0)
    profile_views = models.IntegerField(default=0)
    applications_received = models.IntegerField(default=0)
    messages_received = models.IntegerField(default=0)
    search_appearances = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_employer_analytics"
        unique_together = ["employer", "date"]
        ordering = ["-date"]
