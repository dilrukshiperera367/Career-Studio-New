"""CampusOS — Campus Employers serializers."""

from rest_framework import serializers
from .models import CampusEmployer, EmployerEngagementLog, EmployerMOU, EmployerSatisfactionSurvey, RecruiterContact


class RecruiterContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterContact
        exclude = ["employer"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CampusEmployerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusEmployer
        fields = [
            "id", "name", "slug", "logo", "industry", "company_size", "hq_city",
            "partner_tier", "engagement_status", "total_hires", "is_verified",
        ]


class CampusEmployerDetailSerializer(serializers.ModelSerializer):
    recruiter_contacts = RecruiterContactSerializer(many=True, read_only=True)

    class Meta:
        model = CampusEmployer
        fields = "__all__"
        read_only_fields = [
            "id", "campus", "total_hires", "total_internships",
            "repeat_hiring_score", "follows_count", "created_at", "updated_at",
        ]


class EmployerEngagementLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerEngagementLog
        exclude = ["employer"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployerMOUSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerMOU
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployerSatisfactionSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerSatisfactionSurvey
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
