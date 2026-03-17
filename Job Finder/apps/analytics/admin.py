"""Analytics admin registrations."""
from django.contrib import admin
from .models import SearchLog, PlatformStat, EventLog, EmployerAnalytics


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("query", "user", "results_count", "created_at")
    search_fields = ("query",)
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"


@admin.register(PlatformStat)
class PlatformStatAdmin(admin.ModelAdmin):
    list_display = ("date", "total_users", "total_jobs", "total_applications", "new_users_today")
    date_hierarchy = "date"


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "created_at")
    list_filter = ("event_type",)
    raw_id_fields = ("user",)


@admin.register(EmployerAnalytics)
class EmployerAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("employer", "date", "job_views", "applications_received", "profile_views")
    raw_id_fields = ("employer",)
    date_hierarchy = "date"
