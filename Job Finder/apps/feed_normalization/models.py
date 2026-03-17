"""Feed Normalization — ATS feed sources, deduplication, error logs, disposition sync."""
import uuid
from django.db import models


class FeedSource(models.Model):
    """Registered ATS or external job feed source."""
    class SourceType(models.TextChoices):
        ATS_API = "ats_api", "ATS API Integration"
        XML_FEED = "xml_feed", "XML Job Feed"
        JSON_FEED = "json_feed", "JSON Job Feed"
        CSV_UPLOAD = "csv_upload", "CSV Upload"
        PARTNER_API = "partner_api", "Partner API"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ERROR = "error", "Error State"
        DEPRECATED = "deprecated", "Deprecated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="feed_sources")
    name = models.CharField(max_length=200)
    source_type = models.CharField(max_length=15, choices=SourceType.choices)
    feed_url = models.URLField(max_length=500, blank=True, default="")
    auth_method = models.CharField(max_length=20, blank=True, default="")
    credentials_encrypted = models.TextField(blank=True, default="")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error_message = models.TextField(blank=True, default="")
    total_jobs_imported = models.IntegerField(default=0)
    duplicate_rate = models.FloatField(default=0.0)
    error_rate = models.FloatField(default=0.0)
    quality_score = models.FloatField(default=0.0)
    sync_frequency_minutes = models.IntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_feed_sources"
        ordering = ["-last_sync_at"]

    def __str__(self):
        return f"FeedSource: {self.name} ({self.source_type}, {self.status})"


class FeedDeduplication(models.Model):
    """Records of cross-feed duplicate job detection."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feed_source = models.ForeignKey(FeedSource, on_delete=models.CASCADE, related_name="dedup_records")
    original_job = models.ForeignKey("jobs.JobListing", on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="dedup_originals")
    duplicate_external_id = models.CharField(max_length=200)
    duplicate_title = models.CharField(max_length=300, blank=True, default="")
    similarity_score = models.FloatField(default=0.0)
    detection_method = models.CharField(max_length=50, default="title_hash")
    was_suppressed = models.BooleanField(default=False)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_feed_dedup"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"Dedup: {self.duplicate_external_id} (~{self.similarity_score:.0%} match)"


class FeedErrorLog(models.Model):
    """Feed import error with retry/replay support."""
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feed_source = models.ForeignKey(FeedSource, on_delete=models.CASCADE, related_name="error_logs")
    external_job_id = models.CharField(max_length=200, blank=True, default="")
    raw_payload = models.JSONField(default=dict)
    error_type = models.CharField(max_length=100, blank=True, default="")
    error_message = models.TextField()
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.ERROR)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_feed_error_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["feed_source", "is_resolved"], name="idx_feed_err_source"),
        ]

    def __str__(self):
        return f"FeedError [{self.severity}]: {self.feed_source} — {self.error_type}"


class DispositionSyncRecord(models.Model):
    """ATS disposition/status sync tracking."""
    class SyncStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feed_source = models.ForeignKey(FeedSource, on_delete=models.CASCADE, related_name="disposition_syncs")
    external_application_id = models.CharField(max_length=200)
    ats_stage = models.CharField(max_length=100, blank=True, default="")
    ats_disposition = models.CharField(max_length=100, blank=True, default="")
    platform_application_id = models.UUIDField(null=True, blank=True)
    sync_status = models.CharField(max_length=10, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    error_message = models.TextField(blank=True, default="")
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_disposition_sync_records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DispositionSync: {self.external_application_id} ({self.sync_status})"
