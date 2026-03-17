"""CampusOS — Readiness admin."""

from django.contrib import admin
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


@admin.register(ReadinessCompetency)
class ReadinessCompetencyAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "weight", "is_nace_standard", "is_active"]
    list_filter = ["category", "is_nace_standard", "is_active"]


class CompetencyScoreInline(admin.TabularInline):
    model = CompetencyScore
    extra = 0
    fields = ["competency", "score", "evidence"]
    raw_id_fields = ["competency"]


@admin.register(ReadinessAssessment)
class ReadinessAssessmentAdmin(admin.ModelAdmin):
    list_display = ["student", "assessment_type", "overall_score", "score_label", "status", "assessed_at"]
    list_filter = ["assessment_type", "status"]
    search_fields = ["student__user__first_name", "student__user__last_name"]
    inlines = [CompetencyScoreInline]
    raw_id_fields = ["student", "assessor"]


@admin.register(ImprovementPlan)
class ImprovementPlanAdmin(admin.ModelAdmin):
    list_display = ["title", "student", "status", "progress_pct", "target_completion_date"]
    list_filter = ["status"]
    raw_id_fields = ["student", "created_by"]


@admin.register(PlacementRiskFlag)
class PlacementRiskFlagAdmin(admin.ModelAdmin):
    list_display = ["student", "risk_type", "severity", "status", "created_at"]
    list_filter = ["risk_type", "severity", "status"]
    raw_id_fields = ["student", "flagged_by", "assigned_to"]
