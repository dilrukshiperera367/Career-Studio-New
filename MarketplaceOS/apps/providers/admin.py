from django.contrib import admin
from .models import Provider, ProviderCredential, ProviderBadge, ProviderApplication


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ["display_name", "provider_type", "status", "is_verified", "trust_score", "average_rating"]
    list_filter = ["provider_type", "status", "is_verified", "is_featured", "is_enterprise_approved"]
    search_fields = ["display_name", "headline", "user__email"]
    ordering = ["-trust_score"]
    readonly_fields = ["id", "trust_score", "total_sessions", "total_reviews", "average_rating", "created_at"]


@admin.register(ProviderCredential)
class ProviderCredentialAdmin(admin.ModelAdmin):
    list_display = ["provider", "credential_type", "title", "is_verified"]
    list_filter = ["credential_type", "is_verified"]
    search_fields = ["provider__display_name", "title"]


@admin.register(ProviderBadge)
class ProviderBadgeAdmin(admin.ModelAdmin):
    list_display = ["provider", "badge_type", "awarded_at", "is_active"]
    list_filter = ["badge_type", "is_active"]


@admin.register(ProviderApplication)
class ProviderApplicationAdmin(admin.ModelAdmin):
    list_display = ["provider", "status", "submitted_at", "reviewed_by", "reviewed_at"]
    list_filter = ["status"]
    search_fields = ["provider__display_name"]
