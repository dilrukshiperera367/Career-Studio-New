"""Admin registration for the platform_core app."""

from django.contrib import admin
from .models import (
    AuditLog, TimelineEvent, Notification,
    ApprovalRequest, WebhookSubscription, WebhookDelivery,
)
from .advanced_features import (
    KBCategory, KBArticle,
    BenefitPlan, BenefitEnrollment,
    SkillDefinition, EmployeeSkill,
    GrievanceCase,
)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'entity_type', 'entity_id', 'user', 'tenant', 'ip_address', 'created_at')
    list_filter = ('action', 'entity_type', 'tenant')
    search_fields = ('action', 'entity_type', 'user__email', 'ip_address', 'tenant__name')
    ordering = ['-created_at']
    readonly_fields = [f.name for f in AuditLog._meta.get_fields() if hasattr(f, 'name')]
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'tenant', 'event_type', 'category',
                    'actor', 'actor_type', 'created_at')
    list_filter = ('category', 'actor_type', 'event_type', 'tenant')
    search_fields = ('title', 'description', 'event_type',
                     'employee__first_name', 'employee__last_name', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'metadata')
    raw_id_fields = ('employee', 'actor')
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'recipient', 'type', 'channel', 'is_read', 'read_at', 'created_at')
    list_filter = ('type', 'channel', 'is_read', 'tenant')
    search_fields = ('title', 'body', 'recipient__email', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'read_at')
    raw_id_fields = ('recipient',)
    date_hierarchy = 'created_at'


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'requester', 'approver', 'entity_type', 'action_type',
                    'status', 'step', 'total_steps', 'decided_at', 'created_at')
    list_filter = ('status', 'entity_type', 'action_type', 'tenant')
    search_fields = ('entity_type', 'action_type', 'requester__email', 'approver__email', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'decided_at', 'entity_id')
    raw_id_fields = ('requester', 'approver')
    date_hierarchy = 'created_at'


@admin.register(WebhookSubscription)
class WebhookSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'url', 'is_active', 'created_at')
    list_filter = ('is_active', 'tenant')
    search_fields = ('url', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'secret')


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription', 'event', 'response_status', 'success', 'attempt', 'created_at')
    list_filter = ('success', 'event')
    search_fields = ('event', 'subscription__url', 'error')
    readonly_fields = ('id', 'created_at', 'payload', 'response_body')
    date_hierarchy = 'created_at'


@admin.register(KBCategory)
class KBCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tenant', 'icon', 'parent', 'sort_order', 'article_count')
    list_filter = ('tenant',)
    search_fields = ('name', 'slug', 'tenant__name')
    readonly_fields = ('id',)
    ordering = ('sort_order', 'name')


@admin.register(KBArticle)
class KBArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'category', 'status', 'is_pinned',
                    'view_count', 'helpful_count', 'author', 'created_at')
    list_filter = ('status', 'is_pinned', 'tenant')
    search_fields = ('title', 'excerpt', 'content', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(BenefitPlan)
class BenefitPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'plan_type', 'provider', 'employer_contribution',
                    'employee_contribution', 'is_active', 'created_at')
    list_filter = ('plan_type', 'is_active', 'tenant')
    search_fields = ('name', 'description', 'provider', 'tenant__name')
    readonly_fields = ('id', 'created_at')


@admin.register(BenefitEnrollment)
class BenefitEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'plan', 'status', 'coverage_tier',
                    'effective_date', 'end_date', 'payroll_deduction', 'enrolled_at')
    list_filter = ('status', 'plan', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'plan__name', 'tenant__name')
    readonly_fields = ('id', 'enrolled_at')
    raw_id_fields = ('employee',)
    date_hierarchy = 'effective_date'


@admin.register(SkillDefinition)
class SkillDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'category', 'is_active')
    list_filter = ('category', 'is_active', 'tenant')
    search_fields = ('name', 'description', 'tenant__name')
    readonly_fields = ('id',)
    ordering = ('category', 'name')


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ('employee', 'skill', 'proficiency_level', 'target_level',
                    'verified', 'verified_by', 'last_assessed')
    list_filter = ('verified', 'skill__category')
    search_fields = ('employee__first_name', 'employee__last_name',
                     'employee__employee_number', 'skill__name')
    readonly_fields = ('id',)
    raw_id_fields = ('employee', 'verified_by')


@admin.register(GrievanceCase)
class GrievanceCaseAdmin(admin.ModelAdmin):
    list_display = ('case_number', 'tenant', 'submitted_by', 'category', 'severity',
                    'status', 'is_anonymous', 'assigned_to', 'resolution_date', 'created_at')
    list_filter = ('category', 'severity', 'status', 'is_anonymous', 'tenant')
    search_fields = ('case_number', 'subject', 'description', 'resolution', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'case_number')
    raw_id_fields = ('submitted_by', 'assigned_to')
    date_hierarchy = 'created_at'
