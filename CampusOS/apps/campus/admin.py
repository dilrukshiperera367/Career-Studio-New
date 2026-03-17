"""CampusOS — Campus admin."""

from django.contrib import admin
from .models import AcademicYear, Campus, CampusBranch, Department, Program


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0
    fields = ["name", "code", "is_active"]


class ProgramInline(admin.TabularInline):
    model = Program
    extra = 0
    fields = ["name", "code", "degree_type", "is_active"]


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name", "institution_type", "city", "country", "status", "total_students"]
    list_filter = ["institution_type", "status", "country"]
    search_fields = ["name", "short_name", "slug", "city"]
    prepopulated_fields = {"slug": ("short_name",)}
    inlines = [DepartmentInline]
    fieldsets = (
        ("Identity", {"fields": ("name", "short_name", "slug", "institution_type", "status", "logo", "banner", "website", "description")}),
        ("Location", {"fields": ("address_line1", "address_line2", "city", "state_province", "country", "postal_code")}),
        ("Contact", {"fields": ("email", "phone")}),
        ("Enrollment", {"fields": ("total_students", "active_placement_students")}),
        ("Features", {"fields": (
            "feature_readiness_engine", "feature_internship_management",
            "feature_employer_crm", "feature_placement_drives",
            "feature_alumni_network", "feature_outcomes_analytics",
            "feature_accreditation_reports", "feature_credential_wallet",
        )}),
        ("Settings", {"fields": ("placement_policy", "timezone", "default_language", "academic_year_start_month")}),
        ("Integrations", {"fields": ("sis_institution_id", "lms_institution_id")}),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "campus", "is_active"]
    list_filter = ["campus", "is_active"]
    search_fields = ["name", "code"]
    inlines = [ProgramInline]


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "degree_type", "campus", "department", "duration_years", "is_active"]
    list_filter = ["campus", "degree_type", "is_active"]
    search_fields = ["name", "code"]


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ["name", "campus", "year_start", "year_end", "is_current", "is_placement_season"]
    list_filter = ["campus", "is_current", "is_placement_season"]
