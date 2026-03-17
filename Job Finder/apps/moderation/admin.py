"""Moderation admin registrations."""
from django.contrib import admin
from .models import Report, ModerationAction, BannedEntity


class ModerationActionInline(admin.TabularInline):
    model = ModerationAction
    extra = 0
    readonly_fields = ("action", "moderator", "notes", "created_at")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("content_type", "reason", "reporter", "status", "created_at")
    list_filter = ("status", "reason", "content_type")
    search_fields = ("reporter__email", "description")
    raw_id_fields = ("reporter", "reviewed_by")
    inlines = [ModerationActionInline]


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    list_display = ("report", "action", "moderator", "created_at")
    list_filter = ("action",)


@admin.register(BannedEntity)
class BannedEntityAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "entity_value", "reason", "banned_by", "expires_at", "created_at")
    list_filter = ("entity_type",)
