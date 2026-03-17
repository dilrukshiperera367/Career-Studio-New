"""Promotions Ads — serializers."""
from rest_framework import serializers
from .models import PromotedJobCampaign, PromotedJob, AdClick, SponsoredCompanyPage


class PromotedJobSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_slug = serializers.SlugField(source="job.slug", read_only=True)

    class Meta:
        model = PromotedJob
        fields = ["id", "job_id", "job_title", "job_slug", "boost_factor",
                  "impressions", "clicks", "applications", "spent_lkr", "is_active", "added_at"]


class PromotedJobCampaignSerializer(serializers.ModelSerializer):
    promoted_jobs = PromotedJobSerializer(many=True, read_only=True)
    ctr = serializers.FloatField(read_only=True)
    cpa = serializers.FloatField(read_only=True)

    class Meta:
        model = PromotedJobCampaign
        fields = ["id", "name", "status", "bid_model", "bid_amount_lkr", "daily_budget_lkr",
                  "total_budget_lkr", "spent_lkr", "start_date", "end_date",
                  "impressions", "clicks", "applications", "ctr", "cpa",
                  "promoted_jobs", "created_at"]


class SponsoredCompanyPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SponsoredCompanyPage
        fields = ["id", "placement", "headline", "tagline", "cta_text", "cta_url",
                  "is_active", "impressions", "clicks", "budget_lkr", "spent_lkr",
                  "start_date", "end_date"]
