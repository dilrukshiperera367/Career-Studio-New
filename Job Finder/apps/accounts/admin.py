"""Accounts admin registrations."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User, EmailVerificationToken, PhoneVerificationToken,
    PasswordResetToken, MagicLinkToken, UserSession, LoginAttempt,
    TwoFactorSecret, PushToken,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "phone", "user_type", "is_verified", "is_active", "is_staff", "date_joined")
    list_filter = ("user_type", "is_active", "is_staff", "is_verified")
    search_fields = ("email", "phone")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        ("Personal", {"fields": ("user_type", "preferred_lang", "avatar_url")}),
        ("Verification", {"fields": ("is_verified", "login_method")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("ToS", {"fields": ("tos_accepted_version", "tos_accepted_at")}),
        ("Tracking", {"fields": ("utm_source", "utm_medium", "utm_campaign")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("date_joined",)
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "phone", "user_type", "password1", "password2")}),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "created_at", "expires_at")
    readonly_fields = ("token",)


@admin.register(PhoneVerificationToken)
class PhoneVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "expires_at")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at")
    readonly_fields = ("token",)


@admin.register(MagicLinkToken)
class MagicLinkTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at")
    readonly_fields = ("token",)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "location", "is_trusted", "created_at", "last_active_at")
    list_filter = ("is_trusted",)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("email", "ip_address", "success", "attempted_at")
    list_filter = ("success",)


@admin.register(TwoFactorSecret)
class TwoFactorSecretAdmin(admin.ModelAdmin):
    list_display = ("user", "is_enabled", "created_at")


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "created_at")
    list_filter = ("platform",)
