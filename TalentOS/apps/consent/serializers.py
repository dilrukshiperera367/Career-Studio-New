"""Serializers for consent app."""

from rest_framework import serializers
from apps.consent.models import ConsentRecord, DataRequest


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = [
            "id", "consent_type", "granted", "granted_at", "revoked_at",
            "ip_address", "created_at",
        ]
        read_only_fields = ["id", "granted_at", "revoked_at", "created_at"]


class ConsentGrantSerializer(serializers.Serializer):
    """Input serializer for recording / updating consent."""
    consent_type = serializers.ChoiceField(choices=ConsentRecord.CONSENT_TYPES)
    granted = serializers.BooleanField()


class DataRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataRequest
        fields = [
            "id", "request_type", "status", "result_url", "completed_at", "created_at",
        ]
        read_only_fields = ["id", "status", "result_url", "completed_at", "created_at"]


class DataRequestCreateSerializer(serializers.Serializer):
    """Input serializer for creating a data export or deletion request."""
    request_type = serializers.ChoiceField(choices=DataRequest.REQUEST_TYPES)
