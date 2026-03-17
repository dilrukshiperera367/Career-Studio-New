from django.contrib import admin
from .models import (
    Agency, AgencyClient, AgencyRecruiter, AgencyJobOrder,
    AgencySubmission, AgencyPlacement, AgencyContractor, TalentPool,
)


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ["name", "tier", "is_verified", "total_placements", "active_recruiters", "created_at"]
    list_filter = ["tier", "is_verified", "country"]
    search_fields = ["name", "slug", "contact_email"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(AgencyClient)
class AgencyClientAdmin(admin.ModelAdmin):
    list_display = ["employer_name", "agency", "status", "fee_type", "fee_value", "contract_start"]
    list_filter = ["status", "fee_type", "agency"]
    search_fields = ["employer_name", "employer_contact_email"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(AgencyRecruiter)
class AgencyRecruiterAdmin(admin.ModelAdmin):
    list_display = ["user", "agency", "role", "desk", "is_active", "joined_at"]
    list_filter = ["role", "is_active", "agency"]
    search_fields = ["user__email", "desk"]
    readonly_fields = ["id", "joined_at"]


@admin.register(AgencyJobOrder)
class AgencyJobOrderAdmin(admin.ModelAdmin):
    list_display = ["title", "client", "status", "priority", "positions_count", "filled_count", "created_at"]
    list_filter = ["status", "priority", "employment_type", "is_remote"]
    search_fields = ["title", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(AgencySubmission)
class AgencySubmissionAdmin(admin.ModelAdmin):
    list_display = ["candidate_name", "job_order", "client", "status", "match_score", "created_at"]
    list_filter = ["status", "agency", "client"]
    search_fields = ["candidate_name", "candidate_email"]
    readonly_fields = ["id", "ownership_start", "created_at", "updated_at"]


@admin.register(AgencyPlacement)
class AgencyPlacementAdmin(admin.ModelAdmin):
    list_display = ["submission", "placement_type", "start_date", "fee_amount", "fee_paid", "is_active"]
    list_filter = ["placement_type", "fee_paid", "is_active"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(AgencyContractor)
class AgencyContractorAdmin(admin.ModelAdmin):
    list_display = ["person", "agency", "status", "current_client", "day_rate", "assignment_end"]
    list_filter = ["status", "agency"]
    search_fields = ["person__email"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(TalentPool)
class TalentPoolAdmin(admin.ModelAdmin):
    list_display = ["name", "agency", "is_active", "created_at"]
    list_filter = ["agency", "is_active"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
