from django.contrib import admin
from .models import CommunicationTemplate, CommunicationMessage, CommunicationPreference


@admin.register(CommunicationTemplate)
class CommunicationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel', 'category', 'language', 'is_active']
    list_filter = ['channel', 'category', 'language', 'is_active']
    search_fields = ['name', 'subject']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CommunicationMessage)
class CommunicationMessageAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'channel', 'category', 'status', 'sent_at', 'created_at']
    list_filter = ['channel', 'category', 'status']
    search_fields = ['recipient__email', 'subject']
    readonly_fields = ['sent_at', 'delivered_at', 'opened_at', 'created_at']


@admin.register(CommunicationPreference)
class CommunicationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'sms_enabled', 'push_enabled', 'preferred_language']
    search_fields = ['user__email']
