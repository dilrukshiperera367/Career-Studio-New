"""Reviews admin registrations."""
from django.contrib import admin
from .models import CompanyReview, ReviewHelpful


@admin.register(CompanyReview)
class CompanyReviewAdmin(admin.ModelAdmin):
    list_display = ("employer", "reviewer", "overall_rating", "status", "created_at")
    list_filter = ("status", "overall_rating")
    search_fields = ("employer__company_name_en", "reviewer__email", "title")
    readonly_fields = ("helpful_count",)


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ("review", "user", "created_at")
