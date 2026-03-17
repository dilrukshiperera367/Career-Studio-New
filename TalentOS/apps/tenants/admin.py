"""Admin registrations for the tenants app."""

from django.contrib import admin

from apps.tenants.models import Tenant, TenantSettings
from apps.accounts.models import Subscription


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "plan", "status", "trial_ends_at", "max_jobs", "max_candidates", "created_at"]
    list_filter = ["status", "plan"]
    search_fields = ["name", "slug", "domain"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        ("Identity", {"fields": ("id", "name", "slug", "domain", "logo_url")}),
        ("Plan & Status", {"fields": ("status", "plan", "trial_ends_at")}),
        ("Limits", {"fields": ("max_jobs", "max_candidates")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ["tenant", "data_retention_policy_days", "require_2fa", "pii_masking_enabled", "api_rate_limit_per_minute"]
    list_filter = ["require_2fa", "pii_masking_enabled", "allow_anonymous_apply", "require_consent"]
    search_fields = ["tenant__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        ("Tenant", {"fields": ("id", "tenant")}),
        ("Dedup & Retention", {"fields": ("idle_threshold_days", "retention_days", "candidate_dedup_auto_threshold", "candidate_dedup_flag_threshold", "data_retention_policy_days")}),
        ("Applications", {"fields": ("default_rejection_template", "allow_anonymous_apply", "require_consent")}),
        ("Security", {"fields": ("require_2fa", "session_timeout_minutes", "pii_masking_enabled")}),
        ("API", {"fields": ("api_rate_limit_per_minute",)}),
        ("Configuration", {"fields": ("custom_ranking_weights", "smtp_config", "career_page_config", "custom_fields_config", "notification_preferences_default", "default_onboarding_tasks")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "tenant", "plan", "status", "billing_cycle",
        "trial_end", "stripe_customer_id", "created_at",
    ]
    list_filter = ["status", "billing_cycle"]
    search_fields = ["tenant__name", "stripe_customer_id", "stripe_subscription_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        ("Tenant", {"fields": ("id", "tenant")}),
        ("Plan", {"fields": ("plan", "status", "billing_cycle")}),
        ("Trial", {"fields": ("trial_start", "trial_end", "trial_days", "grace_period_end")}),
        ("Period", {"fields": ("current_period_start", "current_period_end", "canceled_at")}),
        ("Stripe", {"fields": ("stripe_customer_id", "stripe_subscription_id")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
