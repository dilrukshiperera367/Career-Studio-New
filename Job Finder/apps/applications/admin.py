"""Applications admin registrations."""
from django.contrib import admin
from .models import Application, ApplicationStatusHistory


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "notes", "changed_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "match_score", "created_at")
    list_filter = ("status",)
    search_fields = ("applicant__email", "job__title")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("applicant", "job", "resume")
    inlines = [ApplicationStatusHistoryInline]


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "old_status", "new_status", "changed_by", "changed_at")
    readonly_fields = ("changed_at",)
