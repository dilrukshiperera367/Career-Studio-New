from rest_framework import serializers
from .models import (
    Provider, ProviderCredential, ProviderAvailabilitySlot,
    ProviderBlackout, ProviderBadge, ProviderApplication, ProviderContract,
)


class ProviderCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderCredential
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ProviderAvailabilitySlotSerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = ProviderAvailabilitySlot
        fields = "__all__"
        read_only_fields = ["id"]


class ProviderBlackoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderBlackout
        fields = "__all__"
        read_only_fields = ["id"]


class ProviderBadgeSerializer(serializers.ModelSerializer):
    badge_label = serializers.CharField(source="get_badge_type_display", read_only=True)

    class Meta:
        model = ProviderBadge
        fields = "__all__"
        read_only_fields = ["id", "awarded_at"]


class ProviderApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderApplication
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "reviewed_by", "reviewed_at"]


class ProviderSerializer(serializers.ModelSerializer):
    credentials = ProviderCredentialSerializer(many=True, read_only=True)
    badges = ProviderBadgeSerializer(many=True, read_only=True)
    availability_slots = ProviderAvailabilitySlotSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    provider_type_label = serializers.CharField(source="get_provider_type_display", read_only=True)

    class Meta:
        model = Provider
        fields = "__all__"
        read_only_fields = [
            "id", "slug", "trust_score", "total_sessions", "total_reviews",
            "average_rating", "completion_rate", "repeat_booking_rate",
            "profile_completion_pct", "created_at", "updated_at",
        ]


class ProviderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for search/discovery listings."""
    badges = ProviderBadgeSerializer(many=True, read_only=True)
    provider_type_label = serializers.CharField(source="get_provider_type_display", read_only=True)

    class Meta:
        model = Provider
        fields = [
            "id", "slug", "display_name", "headline", "provider_type",
            "provider_type_label", "expertise_categories", "skills",
            "languages", "timezone", "base_rate_lkr", "currency",
            "is_verified", "is_featured", "trust_score", "average_rating",
            "total_sessions", "total_reviews", "response_time_hours",
            "profile_photo_url", "badges",
        ]
