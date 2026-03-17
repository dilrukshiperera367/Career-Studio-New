"""Admin registrations for the workflows app."""

from django.contrib import admin

from apps.workflows.models import AutomationRule, IdempotencyKey, WorkflowExecution, WorkflowStep


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0
    readonly_fields = ["id", "created_at"]
    fields = ["order", "action_type", "delay_hours", "action_config", "condition_json"]
    ordering = ["order"]


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "trigger_type", "enabled", "priority_order", "is_template", "created_at"]
    list_filter = ["trigger_type", "enabled", "is_template", "tenant"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    inlines = [WorkflowStepInline]
    fieldsets = (
        ("Basic Info", {"fields": ("id", "tenant", "name", "description")}),
        ("Trigger", {"fields": ("trigger_type", "conditions_json")}),
        ("Actions", {"fields": ("actions_json",)}),
        ("Config", {"fields": ("enabled", "priority_order", "is_template")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ["rule", "order", "action_type", "delay_hours", "created_at"]
    list_filter = ["action_type"]
    search_fields = ["rule__name", "action_type"]
    readonly_fields = ["id", "created_at"]
    ordering = ["rule", "order"]


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ["action_type", "rule", "tenant", "status", "action_target", "execute_at", "created_at"]
    list_filter = ["status", "action_type", "tenant"]
    search_fields = ["action_type", "action_target", "rule__name"]
    readonly_fields = ["id", "created_at", "tenant", "rule", "step", "event_id", "action_type"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ["key", "tenant", "created_at"]
    list_filter = ["tenant"]
    search_fields = ["key"]
    readonly_fields = ["id", "created_at", "tenant", "key"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
