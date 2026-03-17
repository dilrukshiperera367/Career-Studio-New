from django.contrib import admin
from .models import CrossPlatformSync, LMSIntegration, SISIntegration, SSOConfiguration, WebhookEndpoint


@admin.register(SISIntegration)
class SISIntegrationAdmin(admin.ModelAdmin):
    list_display = ["campus", "sis_type", "sync_frequency", "last_sync_at", "last_sync_status", "is_active"]
    list_filter = ["sis_type", "last_sync_status", "is_active"]


@admin.register(LMSIntegration)
class LMSIntegrationAdmin(admin.ModelAdmin):
    list_display = ["campus", "lms_type", "sync_grades", "last_sync_at", "is_active"]
    list_filter = ["lms_type", "is_active"]


@admin.register(SSOConfiguration)
class SSOConfigurationAdmin(admin.ModelAdmin):
    list_display = ["campus", "protocol", "email_domain", "is_active", "is_mandatory"]
    list_filter = ["protocol", "is_active"]


@admin.register(CrossPlatformSync)
class CrossPlatformSyncAdmin(admin.ModelAdmin):
    list_display = ["campus", "platform", "entity_type", "direction", "status", "last_synced_at"]
    list_filter = ["platform", "entity_type", "status"]


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ["campus", "url", "is_active", "failure_count", "last_triggered_at"]
    list_filter = ["is_active"]
