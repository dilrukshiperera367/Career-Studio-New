"""Admin registrations for the Applications app."""

from django.contrib import admin

from apps.applications.models import (
    Application, StageHistory, Evaluation,
    Interview, InterviewPanel, InterviewScorecard,
    Offer, Employee, OnboardingTask,
)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["id", "candidate", "job", "current_stage", "status", "is_priority", "created_at"]
    list_filter = ["status", "is_priority", "on_hold", "source"]
    search_fields = ["candidate__full_name", "candidate__primary_email", "job__title"]
    raw_id_fields = ["candidate", "job", "current_stage", "resume", "assigned_recruiter", "tenant"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(StageHistory)
class StageHistoryAdmin(admin.ModelAdmin):
    list_display = ["id", "application", "from_stage", "to_stage", "actor", "created_at"]
    list_filter = ["to_stage__stage_type"]
    search_fields = ["application__candidate__full_name", "application__job__title", "notes"]
    raw_id_fields = ["application", "from_stage", "to_stage", "actor", "tenant"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ["id", "application", "stage", "evaluator", "overall_rating", "recommendation", "created_at"]
    list_filter = ["recommendation", "overall_rating"]
    search_fields = ["application__candidate__full_name", "application__job__title", "evaluator__email"]
    raw_id_fields = ["application", "stage", "evaluator", "tenant"]
    readonly_fields = ["id", "created_at"]


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ["id", "application", "interview_type", "status", "date", "time", "created_at"]
    list_filter = ["interview_type", "status"]
    search_fields = ["candidate__full_name", "job__title"]
    raw_id_fields = ["application", "candidate", "job", "interviewer", "tenant"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-date", "-time"]


@admin.register(InterviewPanel)
class InterviewPanelAdmin(admin.ModelAdmin):
    list_display = ["id", "interview", "interviewer", "status", "rating", "submitted_at"]
    list_filter = ["status"]
    raw_id_fields = ["interview", "interviewer", "tenant"]
    readonly_fields = ["id", "created_at"]


@admin.register(InterviewScorecard)
class InterviewScorecardAdmin(admin.ModelAdmin):
    list_display = ["id", "panel", "criteria_name", "rating"]
    raw_id_fields = ["panel"]
    readonly_fields = ["id"]


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ["id", "application", "status", "salary_amount", "salary_currency", "expires_at", "created_at"]
    list_filter = ["status", "salary_currency"]
    search_fields = ["application__candidate__full_name", "application__job__title"]
    raw_id_fields = ["application", "tenant"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["id", "candidate", "title", "department", "status", "start_date", "created_at"]
    list_filter = ["status"]
    search_fields = ["candidate__full_name", "title", "department"]
    raw_id_fields = ["candidate", "application", "job", "manager", "buddy", "tenant"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ["id", "employee", "title", "category", "completed", "due_date"]
    list_filter = ["category", "completed"]
    raw_id_fields = ["employee", "assigned_to", "tenant"]
    readonly_fields = ["id", "created_at"]
