"""Marketplace Search — serializers."""
from rest_framework import serializers
from .models import PersonalizedFeed, JobRecommendation, SearchExplanation, BrowseSurface, TrendingEmployer


class BrowseSurfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowseSurface
        fields = [
            "id", "surface_type", "label", "label_si", "label_ta",
            "slug", "job_count", "icon", "sort_order", "is_featured",
        ]


class JobRecommendationSerializer(serializers.ModelSerializer):
    recommended_job_id = serializers.UUIDField(source="recommended_job.id", read_only=True)
    recommended_job_title = serializers.CharField(source="recommended_job.title", read_only=True)
    recommended_job_slug = serializers.SlugField(source="recommended_job.slug", read_only=True)
    employer_name = serializers.CharField(source="recommended_job.employer.company_name", read_only=True)

    class Meta:
        model = JobRecommendation
        fields = [
            "id", "rec_type", "score", "reasons",
            "recommended_job_id", "recommended_job_title", "recommended_job_slug", "employer_name",
        ]


class SearchExplanationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchExplanation
        fields = [
            "job_id", "matching_skills", "missing_skills", "match_score",
            "salary_match", "location_match", "experience_match", "explanation_text",
        ]


class TrendingEmployerSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="employer.company_name", read_only=True)
    slug = serializers.SlugField(source="employer.slug", read_only=True)
    logo = serializers.ImageField(source="employer.logo", read_only=True)

    class Meta:
        model = TrendingEmployer
        fields = [
            "company_name", "slug", "logo", "job_post_velocity",
            "view_growth_pct", "application_growth_pct", "trending_score", "reasons",
        ]
