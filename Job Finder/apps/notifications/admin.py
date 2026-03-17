"""Notifications admin registrations."""
from django.contrib import admin
from .models import Notification, NotificationPreference, JobAlert


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "channel", "category", "is_read", "created_at")
    list_filter = ("channel", "category", "is_read")
    search_fields = ("user__email", "title")
    raw_id_fields = ("user",)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email_application_updates", "push_application_updates", "sms_application_updates")
    raw_id_fields = ("user",)


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "frequency", "is_active", "last_sent_at")
    list_filter = ("frequency", "is_active")
    raw_id_fields = ("user",)
