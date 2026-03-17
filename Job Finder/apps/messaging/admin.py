"""Messaging admin registrations."""
from django.contrib import admin
from .models import MessageThread, Message


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ("participant_one", "participant_two", "job", "last_message_at", "is_message_request")
    list_filter = ("is_message_request",)
    search_fields = ("participant_one__email", "participant_two__email")
    raw_id_fields = ("participant_one", "participant_two", "job", "application")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "is_read", "created_at")
    list_filter = ("is_read",)
    raw_id_fields = ("thread", "sender")
