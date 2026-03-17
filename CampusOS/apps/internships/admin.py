"""CampusOS — Internships admin."""

from django.contrib import admin
from .models import (
    ExperientialEnrollment,
    ExperientialProgram,
    InternshipApplication,
    InternshipLogbook,
    InternshipOpportunity,
    InternshipRecord,
    SupervisorEvaluation,
    TrainingAgreement,
)


@admin.register(InternshipOpportunity)
class InternshipOpportunityAdmin(admin.ModelAdmin):
    list_display = ["title", "employer_name", "opportunity_type", "status", "campus", "application_deadline"]
    list_filter = ["campus", "opportunity_type", "status", "work_mode", "is_paid"]
    search_fields = ["title", "employer_name"]


@admin.register(InternshipApplication)
class InternshipApplicationAdmin(admin.ModelAdmin):
    list_display = ["student", "opportunity", "status", "faculty_approved", "created_at"]
    list_filter = ["status", "faculty_approved"]
    raw_id_fields = ["student", "opportunity"]


@admin.register(InternshipRecord)
class InternshipRecordAdmin(admin.ModelAdmin):
    list_display = ["student", "employer_name", "role_title", "status", "start_date", "converted_to_fulltime"]
    list_filter = ["campus", "status", "converted_to_fulltime"]
    raw_id_fields = ["student", "application"]


@admin.register(ExperientialProgram)
class ExperientialProgramAdmin(admin.ModelAdmin):
    list_display = ["title", "program_type", "campus", "partner_organization", "is_active"]
    list_filter = ["campus", "program_type", "is_active"]
