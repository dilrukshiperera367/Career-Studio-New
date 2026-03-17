from rest_framework import serializers
from .models import (
    ProviderPlan, ProviderSubscription, MarketplaceCommissionConfig,
    BookingCommission, CourseCommission, FeaturedListingProduct, FeaturedListingPurchase,
    EnterpriseBudget, EnterpriseBudgetTransaction, CoachingBundle,
)


class ProviderPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderPlan
        fields = "__all__"
        read_only_fields = ["id"]


class ProviderSubscriptionSerializer(serializers.ModelSerializer):
    plan_tier = serializers.CharField(source="plan.tier", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = ProviderSubscription
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class MarketplaceCommissionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceCommissionConfig
        fields = "__all__"
        read_only_fields = ["id", "updated_at"]


class BookingCommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingCommission
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class CourseCommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCommission
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class FeaturedListingProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturedListingProduct
        fields = "__all__"
        read_only_fields = ["id"]


class FeaturedListingPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturedListingPurchase
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EnterpriseBudgetSerializer(serializers.ModelSerializer):
    available_amount_lkr = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = EnterpriseBudget
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EnterpriseBudgetTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseBudgetTransaction
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class CoachingBundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachingBundle
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
