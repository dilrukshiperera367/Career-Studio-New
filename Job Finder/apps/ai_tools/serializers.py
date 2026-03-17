"""AI Tools serializers."""
from rest_framework import serializers
from .models import (
    CoverLetter, LinkedInAnalysis, InterviewPrepSession, InterviewAnswer,
    MentorProfile, MentorshipRequest, NetworkingDraft,
    BrandScore, CareerRoadmap,
)


class CoverLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverLetter
        fields = [
            "id", "user", "job_title", "company", "job_description",
            "your_name", "your_skills", "experience", "tone",
            "content", "word_count", "created_at",
        ]
        read_only_fields = ["id", "user", "word_count", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        content = validated_data.get("content", "")
        validated_data["word_count"] = len(content.split())
        return super().create(validated_data)


class LinkedInAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedInAnalysis
        fields = ["id", "user", "headline", "total_score", "max_score",
                  "sections", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class InterviewAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewAnswer
        fields = ["id", "question_id", "answer", "score", "feedback",
                  "time_taken_seconds"]
        read_only_fields = ["id"]


class InterviewPrepSessionSerializer(serializers.ModelSerializer):
    answers = InterviewAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewPrepSession
        fields = ["id", "user", "role", "total_score", "max_score",
                  "completed", "answers", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class MentorProfileSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(
        source="district.name_en", read_only=True, default=""
    )

    class Meta:
        model = MentorProfile
        fields = [
            "id", "user", "name", "title", "company", "industry",
            "district", "district_name", "skills", "bio",
            "years_experience", "hourly_rate_lkr", "is_available",
            "rating", "sessions_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MentorshipRequestSerializer(serializers.ModelSerializer):
    mentor_name = serializers.CharField(source="mentor.name", read_only=True)

    class Meta:
        model = MentorshipRequest
        fields = ["id", "mentor", "mentor_name", "seeker", "message",
                  "status", "created_at"]
        read_only_fields = ["id", "seeker", "created_at"]

    def create(self, validated_data):
        validated_data["seeker"] = self.context["request"].user
        return super().create(validated_data)


class NetworkingDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkingDraft
        fields = ["id", "user", "template_type", "recipient_name",
                  "content", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class BrandScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandScore
        fields = ["id", "user", "total_score", "max_score", "grade",
                  "sections", "computed_at"]
        read_only_fields = ["id", "user", "computed_at"]


class CareerRoadmapSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerRoadmap
        fields = [
            "id", "user", "title", "target_role", "target_salary",
            "timeframe", "milestones", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
