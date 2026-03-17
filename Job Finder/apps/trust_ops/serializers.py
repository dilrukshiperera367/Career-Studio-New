"""Trust Ops — serializers."""
from rest_framework import serializers
from .models import StrikeRecord, SuspensionRecord, ScamAlert, PhishingMessageReport, IdentityProofRequest


class StrikeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrikeRecord
        fields = ["id", "reason", "description", "strike_number", "is_active",
                  "expires_at", "created_at"]


class SuspensionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspensionRecord
        fields = ["id", "suspension_type", "reason", "is_active",
                  "starts_at", "ends_at", "lifted_at", "created_at"]


class ScamAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScamAlert
        fields = ["id", "job_id", "employer_id", "alert_level", "alert_message",
                  "is_public", "is_resolved", "created_at"]


class PhishingMessageReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhishingMessageReport
        fields = ["id", "message_thread_id", "sender_email", "suspicious_url",
                  "description", "screenshot_url", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class IdentityProofRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityProofRequest
        fields = ["id", "trigger_reason", "status", "documents_submitted",
                  "notes", "created_at", "resolved_at"]
