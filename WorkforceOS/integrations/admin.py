"""Admin registration for the integrations app."""

from django.contrib import admin
from .models import Integration, WebhookRegistration, WebhookDeliveryLog


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'connector', 'status', 'last_sync_at', 'created_at')
    list_filter = ('connector', 'status', 'tenant')
    search_fields = ('name', 'tenant__name', 'connector', 'error_message')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_sync_at', 'credentials')
    ordering = ('connector',)


@admin.register(WebhookRegistration)
class WebhookRegistrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'target_url', 'is_active', 'retry_count',
                    'last_triggered_at', 'last_status_code', 'created_at')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name', 'target_url', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_triggered_at', 'secret')


@admin.register(WebhookDeliveryLog)
class WebhookDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'webhook', 'event_type', 'success', 'status_code', 'attempt_count', 'delivered_at')
    list_filter = ('success', 'event_type')
    search_fields = ('event_type', 'webhook__name', 'webhook__target_url')
    readonly_fields = ('id', 'delivered_at', 'payload', 'response_body')
    date_hierarchy = 'delivered_at'
