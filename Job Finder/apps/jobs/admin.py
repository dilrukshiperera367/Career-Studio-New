"""Jobs admin registrations."""
from django.contrib import admin
from .models import JobListing, SavedJob, JobView


@admin.register(JobListing)
class JobListingAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "category", "district", "job_type", "status", "is_featured", "published_at")
    list_filter = ("status", "job_type", "is_featured", "work_arrangement", "category", "district__province")
    search_fields = ("title", "employer__company_name_en", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("view_count", "application_count", "created_at", "updated_at")
    date_hierarchy = "published_at"
    raw_id_fields = ("employer", "category", "subcategory", "industry", "district")
    filter_horizontal = ("required_skills", "preferred_skills")


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "saved_at")
    raw_id_fields = ("user", "job")


@admin.register(JobView)
class JobViewAdmin(admin.ModelAdmin):
    list_display = ("job", "user", "ip_address", "viewed_at")
    raw_id_fields = ("job", "user")
