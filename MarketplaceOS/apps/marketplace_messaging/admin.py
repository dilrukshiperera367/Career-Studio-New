from django.contrib import admin
from .models import MessageThread, Message, MessageAttachment, SystemNotification


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ["id", "thread_type", "participant_a", "participant_b", "status", "is_flagged", "last_message_at"]
    list_filter = ["thread_type", "status", "is_flagged"]
    search_fields = ["participant_a__email", "participant_b__email"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "thread", "sender", "message_type", "status", "is_flagged", "sent_at"]
    list_filter = ["message_type", "status", "is_flagged"]
    search_fields = ["body", "sender__email"]


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "attachment_type", "is_scanned", "is_safe", "uploaded_at"]


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read"]
    search_fields = ["recipient__email", "title"]
