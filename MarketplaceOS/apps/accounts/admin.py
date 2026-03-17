from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "first_name", "last_name", "role", "is_verified", "is_active"]
    list_filter = ["role", "is_verified", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("MarketplaceOS", {"fields": ("role", "phone", "avatar_url", "bio", "timezone", "preferred_language", "is_verified")}),
    )
