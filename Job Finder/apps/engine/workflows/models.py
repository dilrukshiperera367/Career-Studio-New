import uuid
from django.db import models
from django.conf import settings


class WorkflowDefinition(models.Model):
    """
    A configurable workflow template (e.g., Hiring Pipeline, Onboarding, Internal Transfer).
    Organizations can customize stage order, assignees, and automation rules.
    """
    WORKFLOW_HIRING = 'hiring'
    WORKFLOW_ONBOARDING = 'onboarding'
    WORKFLOW_INTERNAL_TRANSFER = 'internal_transfer'
    WORKFLOW_OFFER = 'offer'
    WORKFLOW_REFERRAL = 'referral'
    WORKFLOW_OFFBOARDING = 'offboarding'
    WORKFLOW_REVIEW = 'review'
    WORKFLOW_CUSTOM = 'custom'
    WORKFLOW_TYPE_CHOICES = [
        (WORKFLOW_HIRING, 'Hiring Pipeline'),
        (WORKFLOW_ONBOARDING, 'Onboarding'),
        (WORKFLOW_INTERNAL_TRANSFER, 'Internal Transfer'),
        (WORKFLOW_OFFER, 'Offer Approval'),
        (WORKFLOW_REFERRAL, 'Referral'),
        (WORKFLOW_OFFBOARDING, 'Offboarding'),
        (WORKFLOW_REVIEW, 'Performance Review'),
        (WORKFLOW_CUSTOM, 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    workflow_type = models.CharField(max_length=30, choices=WORKFLOW_TYPE_CHOICES)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        'employers.EmployerAccount', on_delete=models.CASCADE,
        null=True, blank=True, related_name='workflow_definitions',
        help_text='NULL = platform default workflow'
    )
    is_default = models.BooleanField(
        default=False, help_text='Default workflow for this type'
    )
    is_active = models.BooleanField(default=True)
    config = models.JSONField(
        default=dict, blank=True,
        help_text='Custom configuration (automation rules, SLA settings, etc.)'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cx_workflow_definition'
        ordering = ['workflow_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_workflow_type_display()})'


class WorkflowStage(models.Model):
    """A stage/step within a workflow definition."""
    STAGE_STATUS_ACTIVE = 'active'
    STAGE_STATUS_COMPLETED = 'completed'
    STAGE_STATUS_SKIPPED = 'skipped'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.CASCADE, related_name='stages'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(help_text='Stage order in the pipeline')
    is_terminal = models.BooleanField(
        default=False, help_text='Is this a final stage (hired, rejected, completed)?'
    )
    is_automated = models.BooleanField(
        default=False, help_text='Auto-advance when conditions are met'
    )
    required_approvals = models.IntegerField(
        default=0, help_text='Number of approvals needed to advance'
    )
    sla_hours = models.IntegerField(
        null=True, blank=True,
        help_text='Max hours before escalation'
    )
    color = models.CharField(max_length=7, default='#6366f1')
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'cx_workflow_stage'
        ordering = ['workflow', 'order']
        unique_together = ['workflow', 'slug']

    def __str__(self):
        return f'{self.workflow.name} — {self.name}'


class WorkflowInstance(models.Model):
    """A running instance of a workflow for a specific entity."""
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PAUSED = 'paused'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_PAUSED, 'Paused'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        WorkflowDefinition, on_delete=models.PROTECT, related_name='instances'
    )
    current_stage = models.ForeignKey(
        WorkflowStage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='current_instances'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )

    # Generic entity reference
    entity_type = models.CharField(
        max_length=100,
        help_text='Model name (e.g., "Application", "Employee", "InternalApplication")'
    )
    entity_id = models.UUIDField(
        help_text='ID of the entity this workflow tracks'
    )

    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='started_workflows'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_workflows'
    )
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cx_workflow_instance'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.workflow.name} for {self.entity_type}:{self.entity_id}'


class WorkflowTask(models.Model):
    """An actionable task within a workflow instance."""
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_SKIPPED = 'skipped'
    STATUS_OVERDUE = 'overdue'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_SKIPPED, 'Skipped'),
        (STATUS_OVERDUE, 'Overdue'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE, related_name='tasks'
    )
    stage = models.ForeignKey(
        WorkflowStage, on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='workflow_tasks'
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='completed_tasks'
    )
    is_blocking = models.BooleanField(
        default=False, help_text='Blocks workflow advancement until completed'
    )
    requires_human_review = models.BooleanField(
        default=False, help_text='AI governance: requires human checkpoint'
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cx_workflow_task'
        ordering = ['-priority', 'due_date']

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'


class WorkflowTransition(models.Model):
    """Audit log for every state change in a workflow."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE, related_name='transitions'
    )
    from_stage = models.ForeignKey(
        WorkflowStage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transitions_from'
    )
    to_stage = models.ForeignKey(
        WorkflowStage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transitions_to'
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    trigger_type = models.CharField(
        max_length=50, default='manual',
        help_text='manual, automated, api, escalation'
    )
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cx_workflow_transition'
        ordering = ['-created_at']

    def __str__(self):
        from_name = self.from_stage.name if self.from_stage else 'Start'
        to_name = self.to_stage.name if self.to_stage else 'End'
        return f'{from_name} → {to_name}'
