"""CampusOS — Billing serializers."""

from rest_framework import serializers
from .models import (
    CampusBillingEvent,
    CampusInvoice,
    CampusPlan,
    CampusServiceProduct,
    CampusSubscription,
    EmployabilityProgram,
    EmployabilityProgramEnrollment,
    EmployerCampusCampaign,
    PlacementDriveFeeConfig,
    StudentPremiumPlan,
)


class CampusPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusPlan
        fields = "__all__"


class CampusSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()

    class Meta:
        model = CampusSubscription
        fields = "__all__"
        read_only_fields = ["id", "campus"]

    def get_plan_name(self, obj):
        return obj.plan.name


class StudentPremiumPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentPremiumPlan
        fields = "__all__"
        read_only_fields = ["id", "student"]


class EmployerCampusCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerCampusCampaign
        fields = "__all__"
        read_only_fields = ["id"]


class PlacementDriveFeeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementDriveFeeConfig
        fields = "__all__"
        read_only_fields = ["id"]


class EmployabilityProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployabilityProgram
        fields = "__all__"
        read_only_fields = ["id"]


class CampusInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusInvoice
        fields = "__all__"
        read_only_fields = ["id"]


class CampusBillingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusBillingEvent
        fields = "__all__"
        read_only_fields = ["id"]
