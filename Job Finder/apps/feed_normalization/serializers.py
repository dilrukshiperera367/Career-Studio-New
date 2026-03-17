"""Feed Normalization — serializers."""
from rest_framework import serializers
from .models import FeedSource, FeedDeduplication, FeedErrorLog, DispositionSyncRecord


class FeedSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedSource
        fields = ["id", "name", "source_type", "feed_url", "status",
                  "last_sync_at", "last_error_at", "total_jobs_imported",
                  "duplicate_rate", "error_rate", "quality_score", "sync_frequency_minutes"]
        read_only_fields = ["last_sync_at", "last_error_at", "total_jobs_imported",
                            "duplicate_rate", "error_rate"]


class FeedErrorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedErrorLog
        fields = ["id", "feed_source_id", "external_job_id", "error_type",
                  "error_message", "severity", "retry_count", "max_retries",
                  "next_retry_at", "is_resolved", "created_at"]


class DispositionSyncSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispositionSyncRecord
        fields = ["id", "external_application_id", "ats_stage", "ats_disposition",
                  "sync_status", "error_message", "synced_at", "created_at"]
