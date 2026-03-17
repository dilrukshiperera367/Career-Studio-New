"""CampusOS — Readiness serializers."""

from rest_framework import serializers
from .models import (
    CompetencyScore,
    ImprovementPlan,
    ImprovementPlanTask,
    PlacementRiskFlag,
    ReadinessAssessment,
    ReadinessBenchmark,
    ReadinessCompetency,
    ReadinessGapAnalysis,
    WeeklyCareerAction,
)


class ReadinessCompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadinessCompetency
        fields = "__all__"
        read_only_fields = ["id"]


class CompetencyScoreSerializer(serializers.ModelSerializer):
    competency_name = serializers.CharField(source="competency.name", read_only=True)
    competency_category = serializers.CharField(source="competency.category", read_only=True)

    class Meta:
        model = CompetencyScore
        fields = "__all__"
        read_only_fields = ["id"]


class ReadinessAssessmentSerializer(serializers.ModelSerializer):
    competency_scores = CompetencyScoreSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    assessor_name = serializers.CharField(
        source="assessor.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = ReadinessAssessment
        fields = "__all__"
        read_only_fields = ["id", "overall_score", "score_label", "assessed_at", "created_at", "updated_at"]


class ImprovementPlanTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImprovementPlanTask
        exclude = ["plan"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ImprovementPlanSerializer(serializers.ModelSerializer):
    tasks = ImprovementPlanTaskSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = ImprovementPlan
        fields = "__all__"
        read_only_fields = ["id", "progress_pct", "completed_at", "created_at", "updated_at"]


class WeeklyCareerActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyCareerAction
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReadinessGapAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadinessGapAnalysis
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class PlacementRiskFlagSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = PlacementRiskFlag
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "resolved_at"]


class ReadinessBenchmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadinessBenchmark
        fields = "__all__"
        read_only_fields = ["id", "computed_at", "created_at", "updated_at"]
