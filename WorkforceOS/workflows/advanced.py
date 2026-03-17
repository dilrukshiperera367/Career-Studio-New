"""
Advanced Workflow features — complex branching, webhook actions, templates marketplace.
Extends the base workflow engine from Phase 2.
"""

import uuid
import json
import requests
import logging
from django.db import models

logger = logging.getLogger('hrm')


class WorkflowNode(models.Model):
    """Individual node in a complex workflow with branching support."""
    NODE_TYPES = [
        ('trigger', 'Trigger'), ('condition', 'Condition'), ('action', 'Action'),
        ('branch', 'Branch (Parallel)'), ('merge', 'Merge'),
        ('loop', 'Loop'), ('delay', 'Delay'), ('end', 'End'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey('workflows.WorkflowDefinition', on_delete=models.CASCADE, related_name='nodes')
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    name = models.CharField(max_length=200)
    config = models.JSONField(default=dict, help_text="""
        For action: {"action_type":"send_email","template":"welcome","to":"employee.email"}
        For condition: {"field":"employee.department","operator":"equals","value":"Engineering"}
        For branch: {"paths":[{"name":"Path A","next":"node-uuid"},{"name":"Path B","next":"node-uuid"}]}
        For delay: {"duration_minutes":60}
        For loop: {"max_iterations":5,"condition":{"field":"status","operator":"not_equals","value":"complete"}}
    """)
    position_x = models.IntegerField(default=0, help_text="X position in visual builder")
    position_y = models.IntegerField(default=0, help_text="Y position in visual builder")
    next_nodes = models.JSONField(default=list, help_text="List of next node UUIDs")
    sort_order = models.IntegerField(default=0)

    class Meta:
        app_label = 'workflows'
        db_table = 'workflow_nodes'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.name} ({self.node_type})"


class WorkflowTemplate(models.Model):
    """Pre-built workflow templates for the marketplace."""
    CATEGORIES = [
        ('onboarding', 'Onboarding'), ('leave', 'Leave Management'),
        ('attendance', 'Attendance'), ('payroll', 'Payroll'),
        ('birthday', 'Birthday/Anniversary'), ('compliance', 'Compliance'),
        ('helpdesk', 'Helpdesk'), ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORIES)
    icon = models.CharField(max_length=10, default='⚡')
    template_data = models.JSONField(help_text="Serialized workflow definition + nodes")
    install_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_featured = models.BooleanField(default=False)
    is_system = models.BooleanField(default=True, help_text="System-provided vs community")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'workflows'
        db_table = 'workflow_templates'
        ordering = ['-is_featured', '-install_count']

    def __str__(self):
        return f"{self.icon} {self.name}"


# --- Built-in workflow templates ---

BUILT_IN_TEMPLATES = [
    {
        'name': 'New Hire Welcome Email',
        'description': 'Automatically sends a welcome email when a new employee is created',
        'category': 'onboarding',
        'icon': '🎉',
        'template_data': {
            'trigger_event': 'employee.created',
            'conditions': [],
            'actions': [
                {'type': 'send_email', 'template': 'welcome', 'to': '{{employee.email}}',
                 'subject': 'Welcome to the team, {{employee.first_name}}!'},
                {'type': 'send_notification', 'to': '{{employee.manager}}',
                 'message': 'New team member {{employee.full_name}} starts today'},
            ]
        }
    },
    {
        'name': 'Birthday Greeting',
        'description': 'Sends birthday wishes on employee birthdays',
        'category': 'birthday',
        'icon': '🎂',
        'template_data': {
            'trigger_event': 'schedule.daily',
            'conditions': [{'field': 'employee.date_of_birth', 'operator': 'is_today'}],
            'actions': [
                {'type': 'send_email', 'template': 'birthday', 'to': '{{employee.email}}'},
                {'type': 'send_notification', 'to': 'all_employees',
                 'message': '🎂 Happy Birthday {{employee.full_name}}!'},
            ]
        }
    },
    {
        'name': 'Leave Auto-Approve (≤2 days)',
        'description': 'Automatically approves leave requests of 2 days or less',
        'category': 'leave',
        'icon': '✅',
        'template_data': {
            'trigger_event': 'leave.requested',
            'conditions': [{'field': 'leave_request.days', 'operator': 'lte', 'value': 2}],
            'actions': [
                {'type': 'update_field', 'model': 'leave_request', 'field': 'status', 'value': 'approved'},
                {'type': 'send_notification', 'to': '{{employee}}',
                 'message': 'Your leave has been auto-approved'},
            ]
        }
    },
    {
        'name': 'Contract Expiry Reminder',
        'description': 'Sends reminders 30 days before contract expiry',
        'category': 'compliance',
        'icon': '📅',
        'template_data': {
            'trigger_event': 'schedule.daily',
            'conditions': [{'field': 'employee.contract_end_date', 'operator': 'days_until', 'value': 30}],
            'actions': [
                {'type': 'send_notification', 'to': '{{employee.manager}}',
                 'message': '⚠️ {{employee.full_name}}\'s contract expires in 30 days'},
                {'type': 'create_task', 'assignee': 'hr_admin',
                 'title': 'Review contract for {{employee.full_name}}'},
            ]
        }
    },
    {
        'name': 'Probation Review Trigger',
        'description': 'Creates a performance review task before probation ends',
        'category': 'onboarding',
        'icon': '📋',
        'template_data': {
            'trigger_event': 'schedule.daily',
            'conditions': [{'field': 'employee.probation_end_date', 'operator': 'days_until', 'value': 14}],
            'actions': [
                {'type': 'create_approval', 'type_name': 'probation_confirmation',
                 'approver': '{{employee.manager}}'},
                {'type': 'send_email', 'template': 'probation_review', 'to': '{{employee.manager.email}}'},
            ]
        }
    },
]


def execute_webhook_action(config, context):
    """Execute a webhook action — call external API with mapped payload."""
    url = config.get('url')
    method = config.get('method', 'POST').upper()
    headers = config.get('headers', {'Content-Type': 'application/json'})
    payload_template = config.get('payload', {})

    # Template substitution
    payload = json.dumps(payload_template)
    for key, value in context.items():
        payload = payload.replace(f'{{{{{key}}}}}', str(value))

    try:
        response = requests.request(method, url, headers=headers, data=payload, timeout=30)
        return {
            'success': response.status_code < 400,
            'status_code': response.status_code,
            'response': response.text[:500],
        }
    except Exception as e:
        logger.error(f"Webhook action failed: {e}")
        return {'success': False, 'error': str(e)}
