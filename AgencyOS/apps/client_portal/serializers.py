"""Client Portal serializers."""
from rest_framework import serializers
from .models import (
    ClientPortalAccess, PortalJobOrderRequest, PortalShortlistFeedback,
    SecureMessage, IssueEscalation,
)


class ClientPortalAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientPortalAccess
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class PortalJobOrderRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalJobOrderRequest
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class PortalShortlistFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalShortlistFeedback
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class SecureMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecureMessage
        fields = "__all__"
        read_only_fields = ["id", "agency", "sent_at", "read_at"]


class IssueEscalationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueEscalation
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at", "resolved_at"]
