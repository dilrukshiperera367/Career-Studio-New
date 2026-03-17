from rest_framework import serializers
from .models import (
    FeatureFlag, AuditLog, ProviderApprovalQueueItem,
    ReviewModerationAction, CommissionOverride, PlatformAnnouncement,
)


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = ["id", "timestamp"]

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else "system"


class ProviderApprovalQueueSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()

    class Meta:
        model = ProviderApprovalQueueItem
        fields = "__all__"
        read_only_fields = ["id", "submitted_at"]

    def get_provider_name(self, obj):
        return str(obj.provider)


class ReviewModerationActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewModerationAction
        fields = "__all__"
        read_only_fields = ["id", "actioned_at"]


class CommissionOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionOverride
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class PlatformAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAnnouncement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "published_at"]
