"""
Platform Core models — Audit logs, timeline events, notifications,
approvals, webhook subscriptions.
"""

import uuid
from django.db import models
from django.conf import settings


# ============ AUDIT LOG ============

class AuditLog(models.Model):
    """Captures all data mutations system-wide."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    action = models.CharField(max_length=100, help_text="e.g. employee.created, leave.approved")
    entity_type = models.CharField(max_length=50, help_text="Model name (Employee, LeaveRequest, etc.)")
    entity_id = models.UUIDField()
    changes = models.JSONField(default=dict, blank=True, help_text='{"field": {"old": ..., "new": ...}}')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hrm_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at'], name='idx_audit_tenant'),
            models.Index(fields=['tenant', 'entity_type', 'entity_id'], name='idx_audit_entity'),
        ]

    def __str__(self):
        return f"{self.action} by {self.user} at {self.created_at}"


# ============ TIMELINE EVENTS ============

class TimelineEvent(models.Model):
    """Unified employee timeline — every significant action logged here."""
    CATEGORY_CHOICES = [
        ('hr', 'HR Action'), ('leave', 'Leave'), ('attendance', 'Attendance'),
        ('payroll', 'Payroll'), ('performance', 'Performance'),
        ('onboarding', 'Onboarding'), ('document', 'Document'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='timeline_events')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='timeline_events')
    event_type = models.CharField(max_length=100, help_text="e.g. employee.created, leave.approved, payroll.payslip_generated")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    actor_type = models.CharField(max_length=20, default='user', choices=[
        ('user', 'User'), ('system', 'System'), ('automation', 'Workflow Automation'),
    ])
    source_object_type = models.CharField(max_length=50, blank=True)
    source_object_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'timeline_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', '-created_at'], name='idx_timeline_emp'),
            models.Index(fields=['tenant', 'category'], name='idx_timeline_cat'),
        ]

    def __str__(self):
        return f"{self.employee} — {self.title}"


# ============ NOTIFICATIONS ============

class Notification(models.Model):
    """In-app notification for a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    type = models.CharField(max_length=30, default='info', choices=[
        ('info', 'Info'), ('success', 'Success'), ('warning', 'Warning'),
        ('error', 'Error'), ('action', 'Action Required'),
    ])
    channel = models.CharField(max_length=20, default='in_app', choices=[
        ('in_app', 'In-App'), ('email', 'Email'), ('push', 'Push'),
        ('sms', 'SMS'), ('whatsapp', 'WhatsApp'),
    ])
    action_url = models.URLField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at'], name='idx_notif_recipient'),
        ]

    def __str__(self):
        return f"{'🔵' if not self.is_read else '⚪'} {self.title}"


# ============ APPROVAL REQUESTS ============

class ApprovalRequest(models.Model):
    """Generic approval workflow for any entity."""
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='approval_requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='approval_requests_made')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='approval_requests_received')
    entity_type = models.CharField(max_length=50, help_text="e.g. LeaveRequest, JobChange, PayrollRun")
    entity_id = models.UUIDField()
    action_type = models.CharField(max_length=50, help_text="e.g. approve_leave, approve_promotion")
    status = models.CharField(max_length=20, default='pending', choices=STATUS_CHOICES)
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    step = models.IntegerField(default=1, help_text="Step in multi-level approval chain")
    total_steps = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approval_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approver', 'status'], name='idx_approval_approver'),
        ]

    def __str__(self):
        return f"{self.action_type} ({self.status})"


# ============ WEBHOOK SUBSCRIPTIONS ============

class WebhookSubscription(models.Model):
    """Tenant webhook endpoint subscription."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='webhook_subscriptions')
    url = models.URLField(max_length=500)
    events = models.JSONField(default=list, help_text='["employee.created", "leave.approved", ...]')
    secret = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhook_subscriptions'

    def __str__(self):
        return f"{self.url} ({len(self.events)} events)"


class WebhookDelivery(models.Model):
    """Log of webhook delivery attempts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(WebhookSubscription, on_delete=models.CASCADE, related_name='deliveries')
    event = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    attempt = models.IntegerField(default=1)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhook_deliveries'
        ordering = ['-created_at']
from .advanced_features import *
