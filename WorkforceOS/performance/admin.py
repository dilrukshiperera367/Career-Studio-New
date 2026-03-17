"""Admin registration for the performance app."""

from django.contrib import admin
from .models import ReviewCycle, PerformanceReview, Goal, Feedback


@admin.register(ReviewCycle)
class ReviewCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'type', 'start_date', 'end_date',
                    'self_review_deadline', 'manager_review_deadline', 'status', 'created_at')
    list_filter = ('type', 'status', 'tenant')
    search_fields = ('name', 'tenant__name')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'start_date'


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'cycle', 'reviewer', 'self_rating', 'manager_rating',
                    'final_rating', 'calibrated_rating', 'status', 'created_at')
    list_filter = ('status', 'cycle', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'cycle__name', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('employee', 'reviewer', 'calibrated_by')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'tenant', 'type', 'metric_type', 'target_value',
                    'current_value', 'progress', 'status', 'due_date', 'created_at')
    list_filter = ('type', 'metric_type', 'status', 'tenant')
    search_fields = ('title', 'description', 'employee__first_name', 'employee__last_name',
                     'employee__employee_number', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('employee', 'parent_goal')
    date_hierarchy = 'due_date'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_employee', 'to_employee', 'tenant', 'type', 'is_public', 'created_at')
    list_filter = ('type', 'is_public', 'tenant')
    search_fields = ('message', 'from_employee__first_name', 'from_employee__last_name',
                     'to_employee__first_name', 'to_employee__last_name', 'tenant__name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('from_employee', 'to_employee')
    date_hierarchy = 'created_at'
