"""Serializers for tenants app."""

from rest_framework import serializers
from apps.tenants.models import Tenant, TenantSettings
from apps.accounts.models import Subscription


class TenantSerializer(serializers.ModelSerializer):
    trial_days_remaining = serializers.IntegerField(read_only=True)
    is_trial = serializers.BooleanField(read_only=True)
    is_trial_expired = serializers.BooleanField(read_only=True)
    is_in_grace_period = serializers.BooleanField(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "slug", "domain", "logo_url",
            "status", "plan", "trial_ends_at",
            "max_jobs", "max_candidates",
            "is_trial", "trial_days_remaining",
            "is_trial_expired", "is_in_grace_period",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "trial_ends_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    days_remaining = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "status", "billing_cycle",
            "price_per_user", "max_users", "current_users",
            "trial_ends_at", "current_period_start", "current_period_end",
            "days_remaining", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "trial_ends_at"]


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSettings
        fields = [
            "id", "idle_threshold_days", "retention_days",
            "candidate_dedup_auto_threshold", "candidate_dedup_flag_threshold",
            "default_rejection_template",
            "allow_anonymous_apply", "require_consent",
            "custom_ranking_weights", "smtp_config",
        ]
        read_only_fields = ["id"]
