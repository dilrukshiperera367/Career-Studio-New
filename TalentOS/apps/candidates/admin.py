"""Admin registrations for the candidates app."""

from django.contrib import admin

from apps.candidates.models import (
    Candidate,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateIdentity,
    CandidateNote,
    CandidateSkill,
    MergeAudit,
    ResumeDocument,
)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = [
        "full_name", "primary_email", "tenant", "pool_status", "talent_tier",
        "status", "total_experience_years", "most_recent_title", "created_at",
    ]
    list_filter = ["pool_status", "talent_tier", "status", "availability", "tenant", "source"]
    search_fields = ["full_name", "primary_email", "primary_phone", "headline", "most_recent_title"]
    readonly_fields = [
        "id", "created_at", "updated_at", "total_experience_years",
        "most_recent_title", "most_recent_company", "recency_score",
        "resume_completeness",
    ]
    date_hierarchy = "created_at"
    fieldsets = (
        ("Identity", {"fields": ("id", "tenant", "full_name", "primary_email", "primary_phone")}),
        ("Profile", {"fields": ("headline", "location", "location_normalized", "linkedin_url", "github_url", "portfolio_url")}),
        ("Derived Fields", {"fields": ("total_experience_years", "most_recent_title", "most_recent_company", "recency_score", "highest_education", "resume_completeness")}),
        ("Talent Pool", {"fields": ("pool_status", "talent_tier", "availability", "preferred_contact", "rating", "assigned_to", "tags", "source")}),
        ("GDPR / Consent", {"fields": ("consent_given_at", "consent_expires_at", "data_retention_until", "gdpr_deletion_requested_at")}),
        ("Status", {"fields": ("status", "redirect_to")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CandidateIdentity)
class CandidateIdentityAdmin(admin.ModelAdmin):
    list_display = ["candidate", "identity_type", "identity_value", "tenant"]
    list_filter = ["identity_type", "tenant"]
    search_fields = ["identity_value", "candidate__full_name"]
    readonly_fields = ["id"]


@admin.register(ResumeDocument)
class ResumeDocumentAdmin(admin.ModelAdmin):
    list_display = ["candidate", "version", "parse_status", "file_type", "parse_confidence", "created_at"]
    list_filter = ["parse_status", "file_type", "tenant"]
    search_fields = ["candidate__full_name", "file_hash"]
    readonly_fields = ["id", "created_at", "updated_at", "file_hash"]
    date_hierarchy = "created_at"


@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ["canonical_name", "candidate", "confidence", "years_used", "source_section"]
    list_filter = ["source_section", "tenant"]
    search_fields = ["canonical_name", "candidate__full_name"]
    readonly_fields = ["id", "created_at"]


@admin.register(CandidateExperience)
class CandidateExperienceAdmin(admin.ModelAdmin):
    list_display = ["title", "company_name", "candidate", "start_date", "end_date", "is_current"]
    list_filter = ["is_current", "tenant"]
    search_fields = ["title", "company_name", "candidate__full_name", "normalized_title"]
    readonly_fields = ["id", "created_at"]
    date_hierarchy = "start_date"


@admin.register(CandidateEducation)
class CandidateEducationAdmin(admin.ModelAdmin):
    list_display = ["institution", "degree", "field_of_study", "candidate", "start_date", "end_date"]
    list_filter = ["tenant"]
    search_fields = ["institution", "degree", "field_of_study", "candidate__full_name"]
    readonly_fields = ["id", "created_at"]


@admin.register(MergeAudit)
class MergeAuditAdmin(admin.ModelAdmin):
    list_display = ["from_candidate", "to_candidate", "actor", "reason", "created_at"]
    list_filter = ["reason", "tenant"]
    search_fields = ["from_candidate__full_name", "to_candidate__full_name", "actor__email"]
    readonly_fields = ["id", "created_at", "from_candidate", "to_candidate", "actor", "tenant"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CandidateNote)
class CandidateNoteAdmin(admin.ModelAdmin):
    list_display = ["candidate", "author", "is_internal", "created_at"]
    list_filter = ["is_internal", "tenant"]
    search_fields = ["content", "candidate__full_name", "author__email"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"


@admin.register(CandidateCertification)
class CandidateCertificationAdmin(admin.ModelAdmin):
    list_display = ["name", "issuer", "candidate", "issue_date", "expiry_date"]
    list_filter = ["tenant"]
    search_fields = ["name", "issuer", "candidate__full_name", "credential_id"]
    readonly_fields = ["id", "created_at"]
