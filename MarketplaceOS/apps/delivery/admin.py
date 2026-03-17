from django.contrib import admin
from .models import Session, SessionDeliverable, SessionFeedbackForm, SessionAssignment, AsyncReviewDelivery


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["booking", "status", "started_at", "ended_at", "actual_duration_minutes"]
    list_filter = ["status"]
    search_fields = ["booking__reference"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(SessionDeliverable)
class SessionDeliverableAdmin(admin.ModelAdmin):
    list_display = ["title", "deliverable_type", "uploaded_by", "created_at"]
    list_filter = ["deliverable_type", "is_archived"]


@admin.register(SessionFeedbackForm)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = ["session", "source", "overall_rating", "would_rebook", "created_at"]
    list_filter = ["source", "would_rebook"]


@admin.register(AsyncReviewDelivery)
class AsyncReviewAdmin(admin.ModelAdmin):
    list_display = ["session", "review_status", "submitted_at", "delivered_at"]
    list_filter = ["review_status"]
