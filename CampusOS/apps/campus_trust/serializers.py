from rest_framework import serializers
from .models import AbuseReport, AlumniVerification, EmployerVerification, SuspiciousOpportunityFlag, TrustScore


class EmployerVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerVerification
        fields = "__all__"
        read_only_fields = ["id", "verified_by", "verified_at", "trust_score"]


class AlumniVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlumniVerification
        fields = "__all__"
        read_only_fields = ["id", "verified_by", "verified_at"]


class SuspiciousOpportunityFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspiciousOpportunityFlag
        fields = "__all__"
        read_only_fields = ["id", "flagged_by", "status", "resolved_by", "resolved_at"]


class AbuseReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbuseReport
        fields = "__all__"
        read_only_fields = ["id", "reported_by", "status", "actioned_by", "actioned_at"]


class TrustScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustScore
        fields = "__all__"
        read_only_fields = ["id", "user", "score", "flags_count", "abuse_reports_count", "last_computed"]
