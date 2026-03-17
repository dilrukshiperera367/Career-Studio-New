from django.contrib import admin
from .models import AdvisorProfile, AdvisorStudentMapping, InterventionAlert, ResumeApprovalRequest, StudentNote


@admin.register(AdvisorProfile)
class AdvisorProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "campus", "department", "max_caseload", "is_active"]
    list_filter = ["is_active"]
    raw_id_fields = ["user", "campus", "department"]


@admin.register(AdvisorStudentMapping)
class AdvisorStudentMappingAdmin(admin.ModelAdmin):
    list_display = ["advisor", "student", "academic_year", "is_active"]
    list_filter = ["is_active"]
    raw_id_fields = ["advisor", "student"]


@admin.register(StudentNote)
class StudentNoteAdmin(admin.ModelAdmin):
    list_display = ["advisor", "student", "note_type", "is_flagged", "created_at"]
    list_filter = ["note_type", "is_flagged"]


@admin.register(ResumeApprovalRequest)
class ResumeApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ["student", "advisor", "status", "score", "reviewed_at"]
    list_filter = ["status"]


@admin.register(InterventionAlert)
class InterventionAlertAdmin(admin.ModelAdmin):
    list_display = ["student", "alert_type", "severity", "status", "assigned_to"]
    list_filter = ["alert_type", "severity", "status"]
