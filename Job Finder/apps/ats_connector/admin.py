"""ATS Connector admin registrations."""
from django.contrib import admin
from .models import ATSConnection, WebhookLog, JobSyncRecord


@admin.register(ATSConnection)
class ATSConnectionAdmin(admin.ModelAdmin):
    list_display = ("employer", "sync_mode", "is_active", "last_sync_at", "last_sync_status")
    list_filter = ("sync_mode", "is_active", "last_sync_status")
    search_fields = ("employer__company_name",)
    readonly_fields = ("last_sync_at",)


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ("connection", "event_type", "status_code", "created_at")
    list_filter = ("event_type", "status_code")
    readonly_fields = ("created_at",)


@admin.register(JobSyncRecord)
class JobSyncRecordAdmin(admin.ModelAdmin):
    list_display = ("connection", "local_job", "ats_job_id", "last_synced_at")
    list_filter = ("connection",)
    readonly_fields = ("last_synced_at",)
