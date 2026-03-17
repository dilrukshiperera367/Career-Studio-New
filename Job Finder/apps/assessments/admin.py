"""Assessments admin registrations."""
from django.contrib import admin
from .models import Assessment, AssessmentQuestion, AssessmentAttempt


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 0


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "skill", "difficulty", "time_limit_minutes", "is_active", "created_at")
    list_filter = ("is_active", "difficulty", "category")
    search_fields = ("title",)
    inlines = [AssessmentQuestionInline]


@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = ("assessment", "question_type", "sort_order", "points")
    list_filter = ("question_type",)


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ("assessment", "user", "passed", "score", "started_at", "completed_at")
    list_filter = ("passed",)
    raw_id_fields = ("assessment", "user")
