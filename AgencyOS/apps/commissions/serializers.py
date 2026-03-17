"""Commissions serializers."""
from rest_framework import serializers
from .models import CommissionPlan, RecruiterCommissionAssignment, CommissionRecord


class CommissionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionPlan
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class RecruiterCommissionAssignmentSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source="recruiter.get_full_name", read_only=True)

    class Meta:
        model = RecruiterCommissionAssignment
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]


class CommissionRecordSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source="recruiter.get_full_name", read_only=True)

    class Meta:
        model = CommissionRecord
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class CommissionRecordListSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source="recruiter.get_full_name", read_only=True)

    class Meta:
        model = CommissionRecord
        fields = [
            "id", "commission_type", "status", "recruiter", "recruiter_name",
            "gross_commission", "recruiter_amount", "currency", "created_at",
        ]
