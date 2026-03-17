from django.contrib import admin
from .models import (
    SavedProvider, SavedService, ProviderComparison,
    BuyerProfile, MatchRequest, MatchRecommendation, RecommendationFeedback,
)


@admin.register(SavedProvider)
class SavedProviderAdmin(admin.ModelAdmin):
    list_display = ["buyer", "provider", "saved_at"]
    search_fields = ["buyer__email", "provider__display_name"]


@admin.register(SavedService)
class SavedServiceAdmin(admin.ModelAdmin):
    list_display = ["buyer", "service", "saved_at"]


@admin.register(ProviderComparison)
class ProviderComparisonAdmin(admin.ModelAdmin):
    list_display = ["buyer", "label", "created_at"]
    filter_horizontal = ["providers"]


@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ["buyer", "current_role", "target_role", "updated_at"]
    search_fields = ["buyer__email"]


@admin.register(MatchRequest)
class MatchRequestAdmin(admin.ModelAdmin):
    list_display = ["buyer", "provider_type", "service_type", "status", "created_at"]
    list_filter = ["status"]


@admin.register(MatchRecommendation)
class MatchRecommendationAdmin(admin.ModelAdmin):
    list_display = ["match_request", "provider", "rank", "match_score", "source", "was_booked"]
    list_filter = ["source", "was_booked"]


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    list_display = ["recommendation", "feedback_type", "created_at"]
