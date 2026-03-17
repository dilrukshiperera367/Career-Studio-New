"""Contractor Ops serializers."""
from rest_framework import serializers
from .models import Assignment, AssignmentExtension, ContractorDocument, AssignmentIncident, ContractorCheckIn


class AssignmentExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentExtension
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ContractorDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractorDocument
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AssignmentIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentIncident
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ContractorCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractorCheckIn
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class AssignmentSerializer(serializers.ModelSerializer):
    extensions = AssignmentExtensionSerializer(many=True, read_only=True)
    documents = ContractorDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ["id", "agency", "extension_count", "created_at", "updated_at"]


class AssignmentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "id", "candidate", "client_account", "assignment_type", "status",
            "start_date", "current_end_date", "bill_rate_hourly", "currency",
        ]
