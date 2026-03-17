"""CampusOS — Students admin."""

from django.contrib import admin
from .models import (
    CampusReadinessBadge,
    EmployabilityProfile,
    StudentAchievement,
    StudentActivityLog,
    StudentCertification,
    StudentEducation,
    StudentLanguage,
    StudentProfile,
    StudentProject,
    StudentSkill,
)


class StudentSkillInline(admin.TabularInline):
    model = StudentSkill
    extra = 0
    fields = ["name", "skill_type", "proficiency", "is_verified"]


class StudentEducationInline(admin.TabularInline):
    model = StudentEducation
    extra = 0
    fields = ["institution_name", "degree", "start_year", "end_year", "grade"]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user", "campus", "program", "current_year", "cgpa",
        "placement_eligibility", "profile_completion_pct",
    ]
    list_filter = ["campus", "placement_eligibility", "program", "current_year"]
    search_fields = ["user__first_name", "user__last_name", "user__email", "student_id"]
    inlines = [StudentSkillInline, StudentEducationInline]
    raw_id_fields = ["user", "program", "department"]


@admin.register(EmployabilityProfile)
class EmployabilityProfileAdmin(admin.ModelAdmin):
    list_display = ["student", "actively_seeking", "resume_ready", "interview_ready"]
    raw_id_fields = ["student"]


@admin.register(StudentProject)
class StudentProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "student", "is_capstone", "is_featured"]
    raw_id_fields = ["student"]


@admin.register(CampusReadinessBadge)
class CampusReadinessBadgeAdmin(admin.ModelAdmin):
    list_display = ["badge_name", "student", "issued_by", "issued_at", "is_public"]
    raw_id_fields = ["student", "issued_by"]
