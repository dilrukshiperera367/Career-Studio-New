"""Admin registration for the onboarding app."""

from django.contrib import admin
from .models import OnboardingTemplate, OnboardingInstance, OnboardingTask, Asset


@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'status', 'created_at')
    list_filter = ('status', 'tenant')
    search_fields = ('name', 'tenant__name')
    readonly_fields = ('id', 'created_at')


@admin.register(OnboardingInstance)
class OnboardingInstanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'template', 'status', 'completion_pct',
                    'start_date', 'target_completion', 'created_at')
    list_filter = ('status', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'template__name', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('employee',)
    date_hierarchy = 'start_date'


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'instance', 'tenant', 'category', 'assignee', 'due_date',
                    'status', 'sort_order', 'created_at')
    list_filter = ('status', 'category', 'tenant')
    search_fields = ('title', 'description', 'instance__employee__first_name',
                     'instance__employee__last_name', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'completed_at')
    raw_id_fields = ('assignee', 'completed_by')
    date_hierarchy = 'due_date'


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'category', 'serial_number', 'assigned_to',
                    'assigned_date', 'condition', 'status', 'created_at')
    list_filter = ('category', 'condition', 'status', 'tenant')
    search_fields = ('name', 'serial_number', 'assigned_to__first_name',
                     'assigned_to__last_name', 'tenant__name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('assigned_to',)
