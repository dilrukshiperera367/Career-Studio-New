from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class AgencyUserAdmin(UserAdmin):
    list_display = ["email", "username", "role", "is_verified", "is_active", "created_at"]
    list_filter = ["role", "is_verified", "is_active"]
    search_fields = ["email", "username", "first_name", "last_name"]
    readonly_fields = ["id", "created_at", "updated_at", "last_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("Agency Profile", {
            "fields": ("role", "phone", "avatar_url", "bio", "linkedin_url", "timezone", "is_verified", "last_active"),
        }),
    )
