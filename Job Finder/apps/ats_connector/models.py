"""ATS Connector app — Sync configuration, webhook logging, job sync records."""
import uuid
from django.db import models


class ATSConnection(models.Model):
    """Configuration for an employer's ATS integration."""

    class SyncMode(models.TextChoices):
        FULL = "full", "Full ATS Sync"
        WEBHOOK = "webhook", "Basic Webhook"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.OneToOneField("employers.EmployerAccount", on_delete=models.CASCADE, related_name="ats_connection")
    sync_mode = models.CharField(max_length=10, choices=SyncMode.choices, default=SyncMode.MANUAL)
    is_active = models.BooleanField(default=False)

    api_endpoint = models.URLField(max_length=500, blank=True, default="")
    api_key_encrypted = models.TextField(blank=True, default="")
    webhook_secret_encrypted = models.TextField(blank=True, default="")
    webhook_url = models.URLField(max_length=500, blank=True, default="")

    sync_jobs = models.BooleanField(default=True)
    sync_applications = models.BooleanField(default=True)
    sync_candidates = models.BooleanField(default=False)
    sync_interval_minutes = models.IntegerField(default=30)

    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=20, blank=True, default="")
    last_error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_ats_connections"


class WebhookLog(models.Model):
    """Log of incoming/outgoing ATS webhook events."""

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(ATSConnection, on_delete=models.CASCADE, related_name="webhook_logs")
    direction = models.CharField(max_length=10, choices=Direction.choices)
    event_type = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default="")
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_webhook_logs"
        ordering = ["-created_at"]


class JobSyncRecord(models.Model):
    """Tracks sync state between local jobs and ATS jobs."""
    connection = models.ForeignKey(ATSConnection, on_delete=models.CASCADE, related_name="sync_records")
    local_job = models.ForeignKey("jobs.JobListing", on_delete=models.CASCADE, related_name="sync_records")
    ats_job_id = models.CharField(max_length=100)
    ats_job_data = models.JSONField(default=dict)
    last_synced_at = models.DateTimeField(auto_now=True)
    sync_errors = models.JSONField(default=list)

    class Meta:
        db_table = "jf_job_sync_records"
        unique_together = ["connection", "ats_job_id"]
