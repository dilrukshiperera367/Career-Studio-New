from django.contrib import admin
from .models import (
    WorkflowDefinition, WorkflowStage, WorkflowInstance,
    WorkflowTask, WorkflowTransition
)


class WorkflowStageInline(admin.TabularInline):
    model = WorkflowStage
    extra = 1
    ordering = ['order']


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'workflow_type', 'organization', 'is_default', 'is_active']
    list_filter = ['workflow_type', 'is_default', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [WorkflowStageInline]


class WorkflowTaskInline(admin.TabularInline):
    model = WorkflowTask
    extra = 0
    readonly_fields = ['created_at', 'completed_at']


class WorkflowTransitionInline(admin.TabularInline):
    model = WorkflowTransition
    extra = 0
    readonly_fields = ['created_at']


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'entity_type', 'entity_id', 'current_stage',
                    'status', 'started_at']
    list_filter = ['status', 'workflow__workflow_type']
    search_fields = ['entity_id']
    inlines = [WorkflowTaskInline, WorkflowTransitionInline]


@admin.register(WorkflowTask)
class WorkflowTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'instance', 'assigned_to', 'priority',
                    'status', 'due_date', 'is_blocking']
    list_filter = ['status', 'priority', 'is_blocking', 'requires_human_review']
    search_fields = ['title']
