"""
Phase 2 — Workflow Automation Engine models.
Trigger → Condition → Action pattern for automating HR processes.
"""

import uuid
from django.db import models
from django.conf import settings


class WorkflowDefinition(models.Model):
    """Workflow automation rule definition."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    trigger_event = models.CharField(max_length=100, help_text="e.g. employee.created, leave.approved, payroll.finalized")
    trigger_conditions = models.JSONField(default=list, blank=True,
        help_text='[{"field":"department.name","operator":"equals","value":"Engineering"}]')
    actions = models.JSONField(default=list,
        help_text='[{"type":"send_notification","config":{"template":"welcome","to":"employee"}}, '
                  '{"type":"create_task","config":{"title":"...","assignee_role":"hr_admin","due_offset_days":7}}, '
                  '{"type":"update_field","config":{"model":"employee","field":"status","value":"active"}}, '
                  '{"type":"call_webhook","config":{"url":"...","method":"POST"}}, '
                  '{"type":"create_approval","config":{"approver_role":"manager"}}]')
    is_active = models.BooleanField(default=True)
    is_template = models.BooleanField(default=False, help_text="Pre-built workflow from template marketplace")
    run_count = models.IntegerField(default=0)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_definitions'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"


class WorkflowExecution(models.Model):
    """Log of a workflow execution instance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='workflow_executions')
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name='executions')
    trigger_event = models.CharField(max_length=100)
    trigger_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default='running', choices=[
        ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed'),
    ])
    actions_executed = models.JSONField(default=list,
        help_text='[{"action":"send_notification","status":"success","timestamp":"..."}]')
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'workflow_executions'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.workflow.name} — {self.status} ({self.started_at})"
from .advanced import *
