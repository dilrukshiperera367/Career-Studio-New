"""ATS Connector serializers."""
from rest_framework import serializers
from .models import ATSConnection, WebhookLog, JobSyncRecord


class ATSConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATSConnection
        fields = [
            "id", "employer", "sync_mode", "is_active",
            "api_endpoint", "webhook_url",
            "sync_jobs", "sync_applications", "sync_candidates",
            "sync_interval_minutes", "last_sync_at", "last_sync_status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "employer", "webhook_url", "last_sync_at", "last_sync_status", "created_at", "updated_at"]


class ATSConnectionSetupSerializer(serializers.Serializer):
    sync_mode = serializers.ChoiceField(choices=ATSConnection.SyncMode.choices)
    api_endpoint = serializers.URLField(required=False, default="")
    api_key = serializers.CharField(required=False, default="")


class WebhookLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookLog
        fields = [
            "id", "direction", "event_type", "status_code",
            "success", "error_message", "processed_at", "created_at",
        ]
        read_only_fields = fields


class JobSyncRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSyncRecord
        fields = ["id", "local_job", "ats_job_id", "last_synced_at", "sync_errors"]
        read_only_fields = fields
