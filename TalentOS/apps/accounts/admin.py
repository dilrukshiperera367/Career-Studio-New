"""Admin registrations for the accounts app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import (
    BillingHistory,
    EmailVerificationToken,
    InviteToken,
    Notification,
    PasswordResetToken,
    Plan,
    Role,
    User,
    UserNotificationPreference,
    UserRole,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email", "first_name", "last_name", "user_type",
        "tenant", "is_active", "is_staff", "mfa_enabled", "created_at",
    ]
    list_filter = ["user_type", "is_active", "is_staff", "mfa_enabled", "tenant"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        ("Tenant & Role", {"fields": ("tenant", "user_type")}),
        ("Email Verification", {"fields": ("email_verified", "email_verified_at")}),
        ("MFA", {"fields": ("mfa_enabled", "mfa_secret")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "user_type", "tenant", "password1", "password2"),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "created_at"]
    list_filter = ["name", "tenant"]
    search_fields = ["name", "tenant__name"]
    readonly_fields = ["id", "created_at"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "assigned_at"]
    list_filter = ["role__name"]
    search_fields = ["user__email", "role__name"]
    readonly_fields = ["id", "assigned_at"]
    autocomplete_fields = ["user", "role"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "type", "is_read", "created_at"]
    list_filter = ["type", "is_read", "tenant"]
    search_fields = ["title", "body", "user__email"]
    readonly_fields = ["id", "created_at"]
    date_hierarchy = "created_at"


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "email_enabled", "in_app_enabled", "created_at"]
    list_filter = ["event_type", "email_enabled", "in_app_enabled"]
    search_fields = ["user__email", "event_type"]
    readonly_fields = ["id", "created_at"]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "used"]
    list_filter = ["used"]
    search_fields = ["user__email", "token"]
    readonly_fields = ["id", "created_at"]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "used"]
    list_filter = ["used"]
    search_fields = ["user__email", "token"]
    readonly_fields = ["id", "created_at"]


@admin.register(InviteToken)
class InviteTokenAdmin(admin.ModelAdmin):
    list_display = ["email", "tenant", "invited_by", "user_type", "accepted", "created_at", "expires_at"]
    list_filter = ["accepted", "user_type", "tenant"]
    search_fields = ["email", "tenant__name", "invited_by__email"]
    readonly_fields = ["id", "created_at", "accepted_at"]


# ── Subscription & Billing ────────────────────────────────────────────────────

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "tier", "price_monthly", "price_annually", "max_users", "max_jobs", "is_active"]
    list_filter = ["tier", "is_active"]
    search_fields = ["name"]
    ordering = ["tier"]
    readonly_fields = ["id", "created_at"]


# Subscription is registered in apps/tenants/admin.py to keep billing/tenant admin together


@admin.register(BillingHistory)
class BillingHistoryAdmin(admin.ModelAdmin):
    list_display = ["subscription", "amount", "currency", "status", "description", "stripe_invoice_id", "created_at"]
    list_filter = ["status", "currency"]
    search_fields = ["subscription__tenant__name", "stripe_invoice_id"]
    readonly_fields = ["id", "created_at"]
    date_hierarchy = "created_at"
