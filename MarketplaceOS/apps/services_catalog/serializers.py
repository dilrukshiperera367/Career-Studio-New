from rest_framework import serializers
from .models import ServiceCategory, Service, ServicePackage, ServiceAddOn, SavedProvider, SavedService


class ServiceCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = "__all__"
        read_only_fields = ["id"]

    def get_children(self, obj):
        return ServiceCategorySerializer(obj.children.filter(is_active=True), many=True).data


class ServiceAddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceAddOn
        fields = "__all__"
        read_only_fields = ["id"]


class ServicePackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePackage
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ServiceSerializer(serializers.ModelSerializer):
    packages = ServicePackageSerializer(many=True, read_only=True)
    addons = ServiceAddOnSerializer(many=True, read_only=True)
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)
    provider_slug = serializers.CharField(source="provider.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    service_type_label = serializers.CharField(source="get_service_type_display", read_only=True)
    delivery_mode_label = serializers.CharField(source="get_delivery_mode_display", read_only=True)

    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = ["id", "total_bookings", "average_rating", "created_at", "updated_at"]


class ServiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for search/browse listings."""
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)
    provider_slug = serializers.CharField(source="provider.slug", read_only=True)
    provider_photo = serializers.CharField(source="provider.profile_photo_url", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "title", "slug", "service_type", "delivery_mode", "duration_minutes",
            "price_lkr", "currency", "is_free", "compare_at_price_lkr",
            "tags", "skills_covered", "languages", "is_featured",
            "total_bookings", "average_rating",
            "provider_name", "provider_slug", "provider_photo", "category_name",
            "short_description",
        ]


class SavedProviderSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)

    class Meta:
        model = SavedProvider
        fields = "__all__"
        read_only_fields = ["id", "saved_at"]


class SavedServiceSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source="service.title", read_only=True)

    class Meta:
        model = SavedService
        fields = "__all__"
        read_only_fields = ["id", "saved_at"]
