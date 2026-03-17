from django.contrib import admin
from .models import AssessmentBundle, AssessmentSchedule, CampusBenchmarkScore, ProctorFlag, StudentAssessmentAttempt


@admin.register(AssessmentBundle)
class AssessmentBundleAdmin(admin.ModelAdmin):
    list_display = ["title", "assessment_type", "campus", "duration_minutes", "is_proctored", "is_active"]
    list_filter = ["assessment_type", "is_proctored", "is_active"]
    search_fields = ["title"]


@admin.register(AssessmentSchedule)
class AssessmentScheduleAdmin(admin.ModelAdmin):
    list_display = ["bundle", "window_start", "window_end", "venue", "is_active"]
    list_filter = ["is_active"]


@admin.register(StudentAssessmentAttempt)
class StudentAssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ["student", "schedule", "status", "score", "percentage", "is_pass"]
    list_filter = ["status", "is_pass"]
    raw_id_fields = ["student", "schedule"]


@admin.register(ProctorFlag)
class ProctorFlagAdmin(admin.ModelAdmin):
    list_display = ["attempt", "flag_type", "flagged_at", "is_reviewed", "action_taken"]
    list_filter = ["flag_type", "is_reviewed", "action_taken"]


@admin.register(CampusBenchmarkScore)
class CampusBenchmarkScoreAdmin(admin.ModelAdmin):
    list_display = ["bundle", "program", "as_of_date", "avg_score", "pass_rate_pct"]
