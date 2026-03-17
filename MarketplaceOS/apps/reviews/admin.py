from django.contrib import admin
from .models import Review, ProviderResponse, ReviewFlag, OutcomeTag, ReviewSummary


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "reviewer", "provider", "rating_overall", "moderation_status", "is_suspicious", "created_at"]
    list_filter = ["moderation_status", "rating_overall", "is_suspicious", "is_featured"]
    search_fields = ["reviewer__email", "provider__display_name", "body"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        from django.utils import timezone as tz
        queryset.update(moderation_status="approved", moderated_by=request.user, moderated_at=tz.now())

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        from django.utils import timezone as tz
        queryset.update(moderation_status="rejected", moderated_by=request.user, moderated_at=tz.now())

    actions = ["approve_reviews", "reject_reviews"]


@admin.register(ReviewFlag)
class ReviewFlagAdmin(admin.ModelAdmin):
    list_display = ["review", "flagged_by", "reason", "status", "created_at"]
    list_filter = ["reason", "status"]


@admin.register(OutcomeTag)
class OutcomeTagAdmin(admin.ModelAdmin):
    list_display = ["slug", "label", "category", "is_active"]
    list_filter = ["category", "is_active"]


@admin.register(ReviewSummary)
class ReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ["provider", "total_reviews", "avg_overall", "pct_would_rebook", "updated_at"]
    readonly_fields = ["updated_at"]
