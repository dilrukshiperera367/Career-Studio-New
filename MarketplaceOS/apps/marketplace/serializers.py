from rest_framework import serializers
from .models import (
    SavedProvider, SavedService, ProviderComparison,
    BuyerProfile, MatchRequest, MatchRecommendation, RecommendationFeedback,
)


class SavedProviderSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()

    class Meta:
        model = SavedProvider
        fields = "__all__"
        read_only_fields = ["id", "saved_at", "buyer"]

    def get_provider_name(self, obj):
        return str(obj.provider)


class SavedServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.SerializerMethodField()

    class Meta:
        model = SavedService
        fields = "__all__"
        read_only_fields = ["id", "saved_at", "buyer"]

    def get_service_name(self, obj):
        return str(obj.service)


class ProviderComparisonSerializer(serializers.ModelSerializer):
    provider_count = serializers.IntegerField(source="providers.count", read_only=True)

    class Meta:
        model = ProviderComparison
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "buyer"]


class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = "__all__"
        read_only_fields = ["id", "buyer", "updated_at"]


class RecommendationFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationFeedback
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class MatchRecommendationSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()
    feedback = RecommendationFeedbackSerializer(read_only=True)

    class Meta:
        model = MatchRecommendation
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def get_provider_name(self, obj):
        return str(obj.provider)


class MatchRequestSerializer(serializers.ModelSerializer):
    recommendations = MatchRecommendationSerializer(many=True, read_only=True)

    class Meta:
        model = MatchRequest
        fields = "__all__"
        read_only_fields = ["id", "created_at", "buyer", "status"]
