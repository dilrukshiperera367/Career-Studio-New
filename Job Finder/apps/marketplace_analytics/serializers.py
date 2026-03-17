"""Marketplace Analytics — serializers."""
from rest_framework import serializers
from .models import MarketplaceLiquiditySnapshot, FunnelEvent, EmployerROISummary, MarketplaceHealthScore


class LiquiditySnapshotSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name_en", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)

    class Meta:
        model = MarketplaceLiquiditySnapshot
        fields = ["date", "category_name", "district_name", "active_jobs", "seeker_searches",
                  "apply_count", "demand_supply_ratio", "avg_time_to_fill_days"]


class EmployerROISummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerROISummary
        fields = ["week_start", "job_views", "profile_views", "applications",
                  "applications_quality_score", "shortlisted", "hired",
                  "avg_time_to_shortlist_hours", "sponsored_impressions", "sponsored_clicks",
                  "sponsored_spend_lkr", "organic_applies", "sponsored_applies"]


class MarketplaceHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceHealthScore
        fields = "__all__"
