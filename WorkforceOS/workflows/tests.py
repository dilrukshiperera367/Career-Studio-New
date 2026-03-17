"""
Workflows tests — WorkflowDefinition creation, execution logging,
status transitions, trigger-condition structure, and run count tracking.
"""

from django.test import TestCase
from django.utils import timezone

from tenants.models import Tenant
from workflows.models import WorkflowDefinition, WorkflowExecution


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='workflow-test'):
    return Tenant.objects.create(name='Workflow Test Org', slug=slug)


def _make_definition(tenant, trigger='employee.created', active=True):
    return WorkflowDefinition.objects.create(
        tenant=tenant,
        name='Welcome Email on Hire',
        trigger_event=trigger,
        trigger_conditions=[],
        actions=[
            {'type': 'send_notification', 'config': {'template': 'welcome', 'to': 'employee'}},
        ],
        is_active=active,
    )


# ---------------------------------------------------------------------------
# WorkflowDefinition tests
# ---------------------------------------------------------------------------

class TestWorkflowDefinition(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('def-test')

    def test_create_definition(self):
        wf = _make_definition(self.tenant)
        self.assertEqual(wf.trigger_event, 'employee.created')
        self.assertTrue(wf.is_active)

    def test_default_run_count_zero(self):
        wf = _make_definition(self.tenant)
        self.assertEqual(wf.run_count, 0)

    def test_deactivate_workflow(self):
        wf = _make_definition(self.tenant, active=True)
        wf.is_active = False
        wf.save()
        wf.refresh_from_db()
        self.assertFalse(wf.is_active)

    def test_multiple_actions(self):
        wf = WorkflowDefinition.objects.create(
            tenant=self.tenant,
            name='Multi-Action Workflow',
            trigger_event='leave.approved',
            actions=[
                {'type': 'send_notification', 'config': {'template': 'leave_approved', 'to': 'employee'}},
                {'type': 'update_field', 'config': {'model': 'leave_request', 'field': 'status', 'value': 'approved'}},
            ],
        )
        self.assertEqual(len(wf.actions), 2)

    def test_trigger_conditions_stored(self):
        conditions = [
            {'field': 'department.name', 'operator': 'equals', 'value': 'Engineering'}
        ]
        wf = WorkflowDefinition.objects.create(
            tenant=self.tenant,
            name='Dept-Specific Workflow',
            trigger_event='employee.created',
            trigger_conditions=conditions,
            actions=[],
        )
        wf.refresh_from_db()
        self.assertEqual(wf.trigger_conditions[0]['value'], 'Engineering')

    def test_is_template_flag(self):
        wf = WorkflowDefinition.objects.create(
            tenant=self.tenant,
            name='Template Workflow',
            trigger_event='payroll.finalized',
            actions=[],
            is_template=True,
        )
        self.assertTrue(wf.is_template)


# ---------------------------------------------------------------------------
# WorkflowExecution tests
# ---------------------------------------------------------------------------

class TestWorkflowExecution(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('exec-test')
        self.workflow = _make_definition(self.tenant)

    def test_create_execution(self):
        execution = WorkflowExecution.objects.create(
            tenant=self.tenant,
            workflow=self.workflow,
            trigger_event='employee.created',
            trigger_data={'employee_id': 'abc-123'},
        )
        self.assertEqual(execution.status, 'running')
        self.assertEqual(execution.trigger_event, 'employee.created')

    def test_execution_completed(self):
        execution = WorkflowExecution.objects.create(
            tenant=self.tenant,
            workflow=self.workflow,
            trigger_event='employee.created',
            trigger_data={},
        )
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.actions_executed = [
            {'action': 'send_notification', 'status': 'success', 'timestamp': '2024-01-01T12:00:00Z'}
        ]
        execution.save()
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'completed')
        self.assertIsNotNone(execution.completed_at)

    def test_execution_failure_captures_error(self):
        execution = WorkflowExecution.objects.create(
            tenant=self.tenant,
            workflow=self.workflow,
            trigger_event='employee.created',
            trigger_data={},
        )
        execution.status = 'failed'
        execution.error = 'Email server unreachable'
        execution.save()
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'failed')
        self.assertIn('unreachable', execution.error)

    def test_run_count_increment(self):
        """WorkflowDefinition run_count can be incremented on each execution."""
        self.workflow.run_count += 1
        self.workflow.last_run_at = timezone.now()
        self.workflow.save()
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.run_count, 1)

    def test_multiple_executions_per_workflow(self):
        for i in range(3):
            WorkflowExecution.objects.create(
                tenant=self.tenant,
                workflow=self.workflow,
                trigger_event='employee.created',
                trigger_data={'run': i},
            )
        count = WorkflowExecution.objects.filter(workflow=self.workflow).count()
        self.assertEqual(count, 3)

    def test_executions_ordered_newest_first(self):
        WorkflowExecution.objects.create(
            tenant=self.tenant, workflow=self.workflow,
            trigger_event='employee.created', trigger_data={'seq': 1},
        )
        WorkflowExecution.objects.create(
            tenant=self.tenant, workflow=self.workflow,
            trigger_event='employee.created', trigger_data={'seq': 2},
        )
        latest = WorkflowExecution.objects.filter(workflow=self.workflow).first()
        self.assertEqual(latest.trigger_data['seq'], 2)
