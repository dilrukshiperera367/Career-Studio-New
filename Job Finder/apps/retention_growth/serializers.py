"""Retention Growth — serializers."""
from rest_framework import serializers
from .models import RetentionCampaign, InactivityRecord, DigestQueue


class RetentionCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionCampaign
        fields = ["id", "name", "campaign_type", "status", "target_count",
                  "sent_count", "open_count", "click_count", "reactivation_count",
                  "scheduled_at", "created_at"]


class DigestQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigestQueue
        fields = ["id", "job_ids", "digest_type", "scheduled_for", "is_sent", "opened_at"]
