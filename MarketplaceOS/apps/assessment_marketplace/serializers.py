from rest_framework import serializers
from .models import (
    AssessmentVendor, AssessmentProduct, AssessmentRoleMap,
    AssessmentOrder, AssessmentDelivery, AssessmentResult,
)


class AssessmentVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentVendor
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class AssessmentRoleMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentRoleMap
        fields = "__all__"
        read_only_fields = ["id"]


class AssessmentProductSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.vendor_name", read_only=True)
    role_maps = AssessmentRoleMapSerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentProduct
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class AssessmentProductListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.vendor_name", read_only=True)

    class Meta:
        model = AssessmentProduct
        fields = [
            "id", "name", "slug", "category", "delivery_format", "pricing_model",
            "price_per_unit_lkr", "currency", "duration_minutes", "validity_days",
            "vendor_name", "is_featured", "is_active",
        ]


class AssessmentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentResult
        fields = "__all__"
        read_only_fields = ["id", "ingested_at"]


class AssessmentDeliverySerializer(serializers.ModelSerializer):
    result = AssessmentResultSerializer(read_only=True)

    class Meta:
        model = AssessmentDelivery
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class AssessmentOrderSerializer(serializers.ModelSerializer):
    assessment_name = serializers.CharField(source="assessment.name", read_only=True)
    deliveries = AssessmentDeliverySerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentOrder
        fields = "__all__"
        read_only_fields = ["id", "reference", "created_at", "updated_at",
                            "total_price_lkr", "unit_price_lkr"]

    def validate(self, attrs):
        product = attrs.get("assessment")
        if product and not product.is_active:
            raise serializers.ValidationError("This assessment product is not currently available.")
        return attrs

    def create(self, validated_data):
        product = validated_data["assessment"]
        quantity = validated_data.get("quantity", 1)
        validated_data["unit_price_lkr"] = product.price_per_unit_lkr
        validated_data["total_price_lkr"] = product.price_per_unit_lkr * quantity
        return super().create(validated_data)


class AssessmentOrderListSerializer(serializers.ModelSerializer):
    assessment_name = serializers.CharField(source="assessment.name", read_only=True)

    class Meta:
        model = AssessmentOrder
        fields = [
            "id", "reference", "assessment_name", "quantity",
            "total_price_lkr", "status", "created_at",
        ]
