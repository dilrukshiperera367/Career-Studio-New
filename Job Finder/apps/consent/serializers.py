from rest_framework import serializers
from .models import ConsentRecord, DataExportRequest, DataDeletionRequest, PrivacySetting


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DataExportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExportRequest
        fields = "__all__"
        read_only_fields = ["id", "requested_at", "processed_at"]


class DataDeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataDeletionRequest
        fields = "__all__"
        read_only_fields = ["id", "requested_at", "processed_at"]


class PrivacySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySetting
        fields = "__all__"
        read_only_fields = ["id", "updated_at"]
