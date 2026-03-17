"""Agency Compliance serializers."""
from rest_framework import serializers
from .models import CompliancePack, ComplianceChecklist, BackgroundCheck, Credential, ConsentLog


class CompliancePackSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompliancePack
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class ComplianceChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceChecklist
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class BackgroundCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundCheck
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]


class CredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credential
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ConsentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentLog
        fields = "__all__"
        read_only_fields = ["id", "agency"]
