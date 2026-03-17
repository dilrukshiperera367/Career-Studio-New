"""CampusOS — Accounts admin."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import EmailVerificationToken, PasswordResetToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "get_full_name", "role", "campus", "is_active", "is_verified", "date_joined"]
    list_filter = ["role", "is_active", "is_verified", "email_verified", "campus"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone", "profile_photo")}),
        ("Role & Campus", {"fields": ("role", "campus")}),
        ("Status", {"fields": ("is_active", "is_staff", "is_verified", "email_verified", "phone_verified")}),
        ("Privacy", {"fields": ("profile_visibility",)}),
        ("Notifications", {"fields": ("notify_email", "notify_sms", "notify_whatsapp", "notify_push")}),
        ("Consent", {"fields": ("terms_accepted_at", "privacy_accepted_at", "data_processing_consent", "marketing_consent")}),
        ("Permissions", {"fields": ("is_superuser", "groups", "user_permissions")}),
        ("Metadata", {"fields": ("date_joined", "last_login")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )

    readonly_fields = ["date_joined", "last_login"]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "used_at"]
    raw_id_fields = ["user"]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "used_at", "ip_address"]
    raw_id_fields = ["user"]
