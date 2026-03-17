from rest_framework import serializers
from .models import AssessmentBundle, AssessmentSchedule, CampusBenchmarkScore, ProctorFlag, StudentAssessmentAttempt


class AssessmentBundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentBundle
        fields = "__all__"
        read_only_fields = ["id", "campus", "created_by"]


class AssessmentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentSchedule
        fields = "__all__"
        read_only_fields = ["id"]


class StudentAssessmentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAssessmentAttempt
        fields = "__all__"
        read_only_fields = ["id", "student", "started_at", "submitted_at", "score", "percentage", "is_pass", "ip_address"]


class ProctorFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProctorFlag
        fields = "__all__"
        read_only_fields = ["id", "attempt", "flagged_at"]


class CampusBenchmarkScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusBenchmarkScore
        fields = "__all__"
        read_only_fields = ["id"]
