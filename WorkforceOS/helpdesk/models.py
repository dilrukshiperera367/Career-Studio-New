"""
Phase 2 models for HR Helpdesk — Tickets, Categories, SLA, Comments.
"""

import uuid
from django.db import models, transaction
from django.conf import settings


class TicketCategory(models.Model):
    """Category for helpdesk tickets with routing rules."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='ticket_categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    default_assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name='+')
    sla_response_hours = models.IntegerField(default=24)
    sla_resolution_hours = models.IntegerField(default=72)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ticket_categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Ticket(models.Model):
    """HR helpdesk ticket."""
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('medium', 'Medium'),
        ('high', 'High'), ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'), ('in_progress', 'In Progress'),
        ('waiting', 'Waiting on Employee'), ('resolved', 'Resolved'), ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='tickets')
    ticket_number = models.CharField(max_length=20, blank=True)
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='tickets')
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, default='medium', choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, default='open', choices=STATUS_CHOICES)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='assigned_tickets')
    sla_response_due = models.DateTimeField(null=True, blank=True)
    sla_resolution_due = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    sla_response_breached = models.BooleanField(default=False)
    sla_resolution_breached = models.BooleanField(default=False)
    satisfaction_rating = models.IntegerField(null=True, blank=True, help_text="1-5 star rating")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_ticket_status'),
            models.Index(fields=['tenant', 'assigned_to'], name='idx_ticket_assignee'),
        ]

    def __str__(self):
        return f"{self.ticket_number}: {self.subject}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            with transaction.atomic():
                last = Ticket.objects.select_for_update().filter(
                    tenant=self.tenant
                ).order_by('-created_at').first()
                num = 1
                if last and last.ticket_number:
                    try:
                        num = int(last.ticket_number.split('-')[1]) + 1
                    except (IndexError, ValueError):
                        pass
                self.ticket_number = f"TKT-{num:04d}"
        super().save(*args, **kwargs)


class TicketComment(models.Model):
    """Comment/reply on a ticket thread."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    body = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal note, not visible to employee")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ticket_comments'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on {self.ticket.ticket_number}"


# ---------------------------------------------------------------------------
# P1 Upgrades — Service Catalog, Service Requests, Chatbot Intake, SLA Dashboard
# ---------------------------------------------------------------------------

class ServiceCatalogItem(models.Model):
    """HR service catalog item employees can request (e.g. payslip, letter, equipment)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='service_catalog_items')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        TicketCategory, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='catalog_items',
    )
    icon = models.CharField(max_length=100, blank=True, help_text="Icon class or emoji")
    form_schema = models.JSONField(default=dict, blank=True,
        help_text='JSON schema describing fields to collect for this service request')
    fulfillment_sla_hours = models.IntegerField(default=24)
    auto_fulfill = models.BooleanField(default=False,
        help_text="If true, system auto-fulfills without human intervention")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'service_catalog_items'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    """Employee request for a service catalog item."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='service_requests')
    catalog_item = models.ForeignKey(
        ServiceCatalogItem, on_delete=models.CASCADE, related_name='requests',
    )
    ticket = models.OneToOneField(
        Ticket, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='service_request',
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='service_requests',
    )
    form_data = models.JSONField(default=dict, blank=True,
        help_text="Data collected via the catalog item's form_schema")
    status = models.CharField(max_length=30, default='submitted', choices=[
        ('submitted', 'Submitted'), ('in_review', 'In Review'),
        ('approved', 'Approved'), ('fulfilled', 'Fulfilled'),
        ('rejected', 'Rejected'), ('cancelled', 'Cancelled'),
    ])
    fulfillment_notes = models.TextField(blank=True)
    due_by = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'service_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} → {self.catalog_item.name} ({self.status})"


class ChatbotIntake(models.Model):
    """Chatbot conversation log that may result in a ticket being raised."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='chatbot_intakes')
    employee = models.ForeignKey(
        'core_hr.Employee', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='chatbot_sessions',
    )
    session_id = models.CharField(max_length=100, blank=True)
    channel = models.CharField(max_length=30, default='web', choices=[
        ('web', 'Web Widget'), ('mobile', 'Mobile App'),
        ('slack', 'Slack'), ('teams', 'MS Teams'),
    ])
    transcript = models.JSONField(default=list,
        help_text='[{"role":"user","text":"...","ts":"..."}]')
    intent = models.CharField(max_length=100, blank=True,
        help_text="Classified intent, e.g. 'leave_balance', 'payslip', 'policy'")
    resolved_by_bot = models.BooleanField(default=False)
    escalated_ticket = models.ForeignKey(
        Ticket, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='chatbot_intakes',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'chatbot_intakes'
        ordering = ['-started_at']

    def __str__(self):
        return f"Chatbot session {self.session_id} ({self.channel})"


class SLADashboardConfig(models.Model):
    """Per-tenant SLA dashboard configuration and alert thresholds."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE,
                               related_name='sla_dashboard_configs')
    alert_response_breach_pct = models.IntegerField(default=80,
        help_text="Alert when response SLA breach % exceeds this threshold")
    alert_resolution_breach_pct = models.IntegerField(default=80,
        help_text="Alert when resolution SLA breach % exceeds this threshold")
    notify_users = models.JSONField(default=list, blank=True,
        help_text="List of user IDs to notify on SLA breach alerts")
    escalation_policy = models.JSONField(default=dict, blank=True,
        help_text='{"levels":[{"after_hours":4,"notify":[]}]}')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sla_dashboard_configs'

    def __str__(self):
        return f"SLA Config — {self.tenant}"
