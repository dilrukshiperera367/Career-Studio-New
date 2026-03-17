"""Admin registration for the workflows app."""

from django.contrib import admin
from .models import WorkflowDefinition, WorkflowExecution
from .advanced import WorkflowNode, WorkflowTemplate


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'trigger_event', 'is_active', 'is_template',
                    'run_count', 'last_run_at', 'created_by', 'created_at')
    list_filter = ('is_active', 'is_template', 'tenant')
    search_fields = ('name', 'description', 'trigger_event', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'run_count', 'last_run_at')
    ordering = ('name',)


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'workflow', 'tenant', 'trigger_event', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'tenant')
    search_fields = ('trigger_event', 'workflow__name', 'error', 'tenant__name')
    readonly_fields = ('id', 'started_at', 'trigger_data', 'actions_executed')
    date_hierarchy = 'started_at'


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'workflow', 'node_type', 'position_x', 'position_y', 'sort_order')
    list_filter = ('node_type',)
    search_fields = ('name', 'workflow__name')
    readonly_fields = ('id',)
    ordering = ('workflow', 'sort_order')


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'icon', 'install_count', 'rating',
                    'is_featured', 'is_system', 'created_at')
    list_filter = ('category', 'is_featured', 'is_system')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'install_count')
    ordering = ('-is_featured', '-install_count')
