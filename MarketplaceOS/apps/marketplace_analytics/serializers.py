from rest_framework import serializers
from .models import (
    MarketplaceDailySnapshot, ProviderDailySnapshot,
    SearchEvent, BookingFunnelEvent, ProviderViewEvent, RevenueByCategory,
)


class MarketplaceDailySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceDailySnapshot
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ProviderDailySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderDailySnapshot
        fields = "__all__"
        read_only_fields = ["id"]


class SearchEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchEvent
        fields = "__all__"
        read_only_fields = ["id", "timestamp", "user"]


class BookingFunnelEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingFunnelEvent
        fields = "__all__"
        read_only_fields = ["id", "timestamp", "user"]


class ProviderViewEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderViewEvent
        fields = "__all__"
        read_only_fields = ["id", "timestamp", "viewer"]


class RevenueByCategory(serializers.ModelSerializer):
    class Meta:
        model = RevenueByCategory
        fields = "__all__"
        read_only_fields = ["id"]
