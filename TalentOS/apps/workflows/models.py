"""Workflows app — Automation rules, multi-step workflows, executions, and idempotency."""

import uuid
from django.db import models


class AutomationRule(models.Model):
    """Tenant-configurable automation: trigger → conditions → actions."""

    TRIGGER_TYPES = [
        ("application_created", "Application Created"),
        ("stage_changed", "Stage Changed"),
        ("application_idle", "Application Idle"),
        ("application_rejected", "Application Rejected"),
        ("offer_accepted", "Offer Accepted"),
        ("offer_expiring", "Offer Expiring"),
        ("retention_expired", "Retention Expired"),
        ("score_threshold", "Score Threshold Met"),
        ("interview_completed", "Interview Completed"),
        ("feedback_overdue", "Feedback Overdue"),
        ("candidate_updated", "Candidate Profile Updated"),
        ("new_job_match", "New Job Matches Talent Pool"),
        ("probation_milestone", "Probation Milestone"),
        ("application_deadline", "Application Deadline Approaching"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="automation_rules")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_TYPES)
    conditions_json = models.JSONField(
        default=dict, blank=True,
        help_text='e.g. {"to_stage_type": "interview", "score_min": 80}'
    )
    actions_json = models.JSONField(
        default=list,
        help_text='[{"type": "send_email", "template_id": "..."}, ...]'
    )
    enabled = models.BooleanField(default=True)
    priority_order = models.IntegerField(default=0, help_text="Lower = higher priority")
    is_template = models.BooleanField(default=False, help_text="Pre-built workflow recipe")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "automation_rules"
        ordering = ["priority_order"]
        indexes = [
            models.Index(fields=["tenant", "trigger_type", "enabled"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.trigger_type})"


class WorkflowStep(models.Model):
    """Individual step in a multi-step workflow — supports delays and conditions."""

    ACTION_TYPES = [
        ("send_email", "Send Email"),
        ("move_stage", "Move Stage"),
        ("assign_tag", "Assign Tag"),
        ("notify_user", "Notify User"),
        ("set_priority", "Set Priority"),
        ("assign_recruiter", "Assign Recruiter"),
        ("create_task", "Create Task"),
        ("wait", "Wait/Delay"),
        ("condition", "Conditional Branch"),
        ("auto_reject", "Auto Reject"),
        ("escalate", "Escalate"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(AutomationRule, on_delete=models.CASCADE, related_name="steps")
    order = models.IntegerField(default=0)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    action_config = models.JSONField(default=dict, blank=True,
        help_text='{"template_id": "...", "stage_id": "...", "delay_hours": 48}')
    delay_hours = models.FloatField(default=0, help_text="Hours to wait before executing this step")
    condition_json = models.JSONField(default=dict, blank=True,
        help_text='{"if_score_above": 80, "else_goto_step": 3}')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_steps"
        ordering = ["rule", "order"]

    def __str__(self):
        return f"Step {self.order}: {self.action_type}"


class WorkflowExecution(models.Model):
    """Record of a workflow action execution (for auditing)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    rule = models.ForeignKey(AutomationRule, on_delete=models.CASCADE, related_name="executions")
    step = models.ForeignKey(WorkflowStep, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="executions")
    event_id = models.UUIDField(db_index=True)
    action_type = models.CharField(max_length=50)
    action_target = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[("success", "Success"), ("failed", "Failed"), ("skipped", "Skipped"),
                 ("pending", "Pending"), ("delayed", "Delayed")],
        default="success",
    )
    error = models.TextField(blank=True, default="")
    execute_at = models.DateTimeField(null=True, blank=True, help_text="For delayed executions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_executions"
        indexes = [
            models.Index(fields=["tenant", "execute_at"]),
        ]

    def __str__(self):
        return f"{self.action_type} — {self.status}"


class IdempotencyKey(models.Model):
    """Prevents duplicate execution of async actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "idempotency_keys"
        unique_together = [("tenant", "key")]
        indexes = [
            models.Index(fields=["tenant", "key"]),
        ]

    def __str__(self):
        return self.key


class WebhookSubscription(models.Model):
    """Tenant-configured endpoint to receive outbound webhook events."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='webhook_subscriptions')
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=200, blank=True, help_text='HMAC signing secret')
    events = models.JSONField(default=list, help_text='List of event types to subscribe to, e.g. ["candidate.created"]')
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Webhook Subscription'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.tenant} → {self.url}'


class ApprovalChainInstance(models.Model):
    """
    A live approval chain instance for an object requiring multi-level sign-off
    (e.g. offer approval, headcount requisition, job publishing).
    """

    OBJECT_TYPE_CHOICES = [
        ("offer", "Offer"),
        ("job", "Job"),
        ("headcount_plan", "Headcount Plan"),
        ("compensation", "Compensation Change"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="approval_chain_instances")
    object_type = models.CharField(max_length=30, choices=OBJECT_TYPE_CHOICES)
    object_id = models.UUIDField(db_index=True, help_text="PK of the object being approved")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    current_step = models.IntegerField(default=1)
    total_steps = models.IntegerField(default=1)
    initiated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="initiated_approvals",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "approval_chain_instances"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "object_type", "object_id"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self):
        return f"Approval ({self.object_type}:{self.object_id}) — {self.status}"


class ApprovalStepInstance(models.Model):
    """A single step within an ApprovalChainInstance."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("skipped", "Skipped"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chain = models.ForeignKey(ApprovalChainInstance, on_delete=models.CASCADE, related_name="steps")
    step_number = models.IntegerField()
    approver = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approval_step_instances",
    )
    role_label = models.CharField(max_length=100, blank=True, default="",
        help_text="e.g. 'Finance Director', 'VP Engineering'")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True, default="")
    acted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approval_step_instances"
        ordering = ["chain", "step_number"]
        unique_together = [("chain", "step_number")]

    def __str__(self):
        return f"Step {self.step_number} ({self.status})"


class SLAEscalationRule(models.Model):
    """
    Defines when and how to escalate if an SLA is breached.
    Linked to pipeline stages or approval chains.
    """

    TRIGGER_CHOICES = [
        ("stage_sla_breach", "Stage SLA Breach"),
        ("approval_overdue", "Approval Overdue"),
        ("feedback_overdue", "Feedback Overdue"),
        ("offer_expiring", "Offer Expiring"),
    ]

    ESCALATION_ACTION_CHOICES = [
        ("notify_manager", "Notify Manager"),
        ("notify_recruiter", "Notify Recruiter"),
        ("auto_reassign", "Auto-Reassign"),
        ("slack_alert", "Slack Alert"),
        ("email_chain", "Email Escalation Chain"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sla_escalation_rules")
    name = models.CharField(max_length=200)
    trigger = models.CharField(max_length=30, choices=TRIGGER_CHOICES)
    threshold_hours = models.IntegerField(help_text="Hours after SLA deadline before escalation fires")
    escalation_action = models.CharField(max_length=30, choices=ESCALATION_ACTION_CHOICES)
    escalation_config = models.JSONField(
        default=dict, blank=True,
        help_text='{"notify_user_ids": [...], "slack_channel": "..."}'
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sla_escalation_rules"
        ordering = ["threshold_hours"]

    def __str__(self):
        return f"SLA Rule: {self.name} ({self.trigger})"
