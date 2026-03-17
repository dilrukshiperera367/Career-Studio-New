"""Agency CRM serializers."""
from rest_framework import serializers
from .models import ProspectCompany, ClientAccount, ClientContact, Opportunity, ActivityLog, RateCard, AccountPlan


class ProspectCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProspectCompany
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class ClientContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientContact
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class ClientAccountSerializer(serializers.ModelSerializer):
    contacts = ClientContactSerializer(many=True, read_only=True)

    class Meta:
        model = ClientAccount
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = "__all__"
        read_only_fields = ["id", "agency", "weighted_value", "created_at", "updated_at"]


class ActivityLogSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True
    )

    class Meta:
        model = ActivityLog
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]


class RateCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateCard
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class AccountPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountPlan
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]
