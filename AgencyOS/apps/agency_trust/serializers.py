"""Agency Trust serializers."""
from rest_framework import serializers
from .models import AgencyTrustProfile, AbuseReport, SuspiciousActivityLog, AuditLog


class AgencyTrustProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyTrustProfile
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class AbuseReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbuseReport
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]


class SuspiciousActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspiciousActivityLog
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]
