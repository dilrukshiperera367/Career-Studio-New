"""Admin registration for the analytics app."""

from django.contrib import admin
from .ai_analytics import CustomDashboard, DashboardWidget


@admin.register(CustomDashboard)
class CustomDashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_default', 'is_shared', 'created_by', 'created_at')
    list_filter = ('is_default', 'is_shared', 'tenant')
    search_fields = ('name', 'description', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'dashboard', 'tenant', 'widget_type', 'data_source', 'position_x', 'position_y')
    list_filter = ('widget_type', 'data_source', 'tenant')
    search_fields = ('title', 'dashboard__name', 'tenant__name')
    readonly_fields = ('id',)
    ordering = ('position_y', 'position_x')
