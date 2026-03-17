from rest_framework import serializers
from .models import (
    EnterpriseAccount, EnterpriseTeamMember, EnterpriseBudget, EnterpriseBudgetAlloc,
    EnterpriseApprovedProvider, EnterpriseCatalogItem, EnterpriseBookingApproval,
    InternalMentorProgram, InternalMentorMatch,
)


class EnterpriseTeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseTeamMember
        fields = "__all__"
        read_only_fields = ["id", "joined_at"]


class EnterpriseBudgetAllocSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseBudgetAlloc
        fields = "__all__"
        read_only_fields = ["id", "spent_lkr", "allocated_at"]


class EnterpriseBudgetSerializer(serializers.ModelSerializer):
    allocations = EnterpriseBudgetAllocSerializer(many=True, read_only=True)
    available_amount_lkr = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = EnterpriseBudget
        fields = "__all__"
        read_only_fields = ["id", "spent_amount_lkr", "allocated_amount_lkr", "created_at"]


class EnterpriseApprovedProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseApprovedProvider
        fields = "__all__"
        read_only_fields = ["id", "approved_at"]


class EnterpriseCatalogItemSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source="service.title", read_only=True)

    class Meta:
        model = EnterpriseCatalogItem
        fields = "__all__"
        read_only_fields = ["id", "added_at"]


class EnterpriseBookingApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseBookingApproval
        fields = "__all__"
        read_only_fields = ["id", "status", "decided_at", "created_at"]


class EnterpriseAccountSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = EnterpriseAccount
        fields = "__all__"
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class InternalMentorMatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalMentorMatch
        fields = "__all__"
        read_only_fields = ["id", "matched_at"]


class InternalMentorProgramSerializer(serializers.ModelSerializer):
    matches = InternalMentorMatchSerializer(many=True, read_only=True)

    class Meta:
        model = InternalMentorProgram
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
