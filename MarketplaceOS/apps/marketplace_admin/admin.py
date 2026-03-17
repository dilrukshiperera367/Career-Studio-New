from django.contrib import admin
from .models import (
    FeatureFlag, AuditLog, ProviderApprovalQueueItem,
    ReviewModerationAction, CommissionOverride, PlatformAnnouncement,
)


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ["key", "is_enabled", "rollout_percentage", "updated_at"]
    list_editable = ["is_enabled", "rollout_percentage"]
    search_fields = ["key"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action_type", "actor", "target_model", "target_id", "timestamp"]
    list_filter = ["action_type"]
    search_fields = ["actor__email", "target_id"]
    readonly_fields = ["id", "timestamp", "actor", "action_type", "before_state", "after_state"]


@admin.register(ProviderApprovalQueueItem)
class ProviderApprovalQueueAdmin(admin.ModelAdmin):
    list_display = ["provider", "status", "priority", "assigned_to", "submitted_at", "reviewed_at"]
    list_filter = ["status", "priority"]
    search_fields = ["provider__user__email"]


@admin.register(ReviewModerationAction)
class ReviewModerationActionAdmin(admin.ModelAdmin):
    list_display = ["review", "moderator", "decision", "actioned_at"]
    list_filter = ["decision"]


@admin.register(CommissionOverride)
class CommissionOverrideAdmin(admin.ModelAdmin):
    list_display = ["provider", "commission_percent", "valid_from", "valid_until", "approved_by"]


@admin.register(PlatformAnnouncement)
class PlatformAnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "target_audience", "is_published", "published_at", "expires_at"]
    list_filter = ["target_audience", "is_published"]
    list_editable = ["is_published"]
