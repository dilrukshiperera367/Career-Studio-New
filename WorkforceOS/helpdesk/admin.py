"""Admin registration for the helpdesk app."""

from django.contrib import admin
from .models import TicketCategory, Ticket, TicketComment


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'sla_response_hours', 'sla_resolution_hours',
                    'default_assignee', 'sort_order', 'is_active')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name', 'description', 'tenant__name')
    readonly_fields = ('id',)
    ordering = ('sort_order', 'name')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'subject', 'tenant', 'employee', 'category', 'priority',
                    'status', 'assigned_to', 'sla_response_breached', 'sla_resolution_breached',
                    'satisfaction_rating', 'created_at')
    list_filter = ('status', 'priority', 'category', 'sla_response_breached',
                   'sla_resolution_breached', 'tenant')
    search_fields = ('ticket_number', 'subject', 'description', 'employee__first_name',
                     'employee__last_name', 'tenant__name')
    readonly_fields = ('id', 'ticket_number', 'created_at', 'updated_at',
                       'first_response_at', 'resolved_at')
    raw_id_fields = ('employee', 'assigned_to')
    date_hierarchy = 'created_at'


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal',)
    search_fields = ('body', 'ticket__ticket_number', 'ticket__subject', 'author__email')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('ticket', 'author')
