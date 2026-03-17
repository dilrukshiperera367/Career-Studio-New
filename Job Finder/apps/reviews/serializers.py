"""Reviews serializers."""
from rest_framework import serializers
from .models import CompanyReview, ReviewHelpful, EmployerReviewResponse


class EmployerResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerReviewResponse
        fields = ["id", "response_text", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CompanyReviewSerializer(serializers.ModelSerializer):
    employer_response = EmployerResponseSerializer(read_only=True)
    user_marked_helpful = serializers.SerializerMethodField()
    reviewer_display = serializers.SerializerMethodField()

    class Meta:
        model = CompanyReview
        fields = [
            "id", "employer", "is_anonymous", "relationship",
            "overall_rating", "work_life_balance", "career_growth",
            "compensation", "management", "culture",
            "title", "pros", "cons", "advice_to_management",
            "job_title", "employment_duration_months",
            "status", "helpful_count", "report_count",
            "employer_response", "user_marked_helpful", "reviewer_display",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "helpful_count", "report_count", "created_at", "updated_at"]

    def get_user_marked_helpful(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.helpful_votes.filter(user=request.user).exists()

    def get_reviewer_display(self, obj):
        if obj.is_anonymous:
            return "Anonymous Employee"
        if obj.reviewer:
            profile = getattr(obj.reviewer, "seeker_profile", None)
            if profile:
                return f"{profile.first_name} {profile.last_name}".strip()
            return obj.reviewer.email.split("@")[0]
        return "Former Employee"


class CompanyReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyReview
        fields = [
            "employer", "is_anonymous", "relationship",
            "overall_rating", "work_life_balance", "career_growth",
            "compensation", "management", "culture",
            "title", "pros", "cons", "advice_to_management",
            "job_title", "employment_duration_months",
        ]

    def validate_overall_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

