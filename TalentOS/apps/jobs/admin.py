"""Admin registrations for the jobs app."""

from django.contrib import admin

from apps.jobs.models import Job, JobTemplate, PipelineStage


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "title", "tenant", "status", "priority", "employment_type",
        "department", "location", "headcount_target", "headcount_filled",
        "created_by", "created_at",
    ]
    list_filter = ["status", "priority", "employment_type", "is_remote", "internal_only", "tenant"]
    search_fields = ["title", "slug", "department", "location", "requisition_id"]
    readonly_fields = ["id", "created_at", "updated_at", "view_count", "published_at", "closed_at"]
    date_hierarchy = "created_at"
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Basic Info", {"fields": ("id", "tenant", "title", "slug", "status", "priority")}),
        ("Details", {"fields": ("department", "location", "locations", "is_remote", "employment_type", "internal_only")}),
        ("Content", {"fields": ("description", "requirements", "screening_questions")}),
        ("Matching Config", {"fields": ("required_skills", "optional_skills", "target_titles", "min_years_experience", "max_years_experience", "domain_tags")}),
        ("Compensation", {"fields": ("salary_min", "salary_max", "salary_currency")}),
        ("Headcount & Deadlines", {"fields": ("headcount_target", "headcount_filled", "application_deadline", "requisition_id")}),
        ("Ownership", {"fields": ("created_by", "hiring_manager", "template_source")}),
        ("Metrics", {"fields": ("view_count", "published_at", "closed_at", "created_at", "updated_at")}),
    )


@admin.register(JobTemplate)
class JobTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "title", "tenant", "department", "employment_type", "created_at"]
    list_filter = ["employment_type", "tenant"]
    search_fields = ["name", "title", "department"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = ["name", "job", "stage_type", "order", "is_terminal", "sla_days", "tenant"]
    list_filter = ["stage_type", "is_terminal", "tenant"]
    search_fields = ["name", "job__title"]
    readonly_fields = ["id", "created_at"]
    ordering = ["job", "order"]
