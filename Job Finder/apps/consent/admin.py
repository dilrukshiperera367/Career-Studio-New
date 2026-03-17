from django.contrib import admin
from .models import ConsentRecord, DataExportRequest, DataDeletionRequest, PrivacySetting


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "consent_type", "is_granted", "version", "granted_at", "revoked_at"]
    list_filter = ["consent_type", "is_granted"]
    search_fields = ["user__email"]


@admin.register(DataExportRequest)
class DataExportRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "format", "requested_at", "processed_at"]
    list_filter = ["status"]


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ["user", "scope", "status", "requested_at", "processed_at"]
    list_filter = ["status", "scope"]


@admin.register(PrivacySetting)
class PrivacySettingAdmin(admin.ModelAdmin):
    list_display = ["user", "profile_visibility", "show_email", "allow_recruiter_messages", "show_in_search"]
    list_filter = ["profile_visibility"]
