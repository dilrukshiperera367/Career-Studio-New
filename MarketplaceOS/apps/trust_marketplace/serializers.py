from rest_framework import serializers
from .models import ProviderReport, ProviderStrike, Dispute, DisputeResolution, RiskFlag, QualityScore, BackgroundCheckRecord


class ProviderReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderReport
        fields = "__all__"
        read_only_fields = ["id", "status", "assigned_to", "resolution_notes", "resolved_at", "created_at", "updated_at"]


class ProviderStrikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderStrike
        fields = "__all__"
        read_only_fields = ["id", "issued_at"]


class DisputeResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeResolution
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class DisputeSerializer(serializers.ModelSerializer):
    resolutions = DisputeResolutionSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Dispute
        fields = "__all__"
        read_only_fields = ["id", "reference", "status", "assigned_to", "resolved_at", "created_at", "updated_at"]


class RiskFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskFlag
        fields = "__all__"
        read_only_fields = ["id", "detected_at"]


class QualityScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityScore
        fields = "__all__"
        read_only_fields = ["computed_at"]


class BackgroundCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundCheckRecord
        fields = "__all__"
        read_only_fields = ["id", "requested_at"]
