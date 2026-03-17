"""Vendor / VMS serializers."""
from rest_framework import serializers
from .models import VMSIntegration, VMSJobFeed, VendorScorecard, SubcontractorPartner


class VMSIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VMSIntegration
        fields = "__all__"
        read_only_fields = ["id", "agency", "last_sync_at", "created_at", "updated_at"]
        extra_kwargs = {"api_key_hint": {"read_only": True}}


class VMSJobFeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = VMSJobFeed
        fields = "__all__"
        read_only_fields = ["id", "ingested_at", "updated_at"]


class VendorScorecardSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorScorecard
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]


class SubcontractorPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubcontractorPartner
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]
