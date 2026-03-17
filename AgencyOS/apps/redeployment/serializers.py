"""Redeployment serializers."""
from rest_framework import serializers
from .models import RedeploymentPool, RedeploymentPoolMember, EndingAssignmentAlert, RedeploymentOpportunity


class RedeploymentPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedeploymentPool
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class RedeploymentPoolMemberSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()

    class Meta:
        model = RedeploymentPoolMember
        fields = "__all__"
        read_only_fields = ["id", "added_at", "updated_at"]

    def get_candidate_name(self, obj):
        return f"{obj.candidate.first_name} {obj.candidate.last_name}"


class EndingAssignmentAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = EndingAssignmentAlert
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class RedeploymentOpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RedeploymentOpportunity
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]
