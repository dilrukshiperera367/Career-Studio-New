"""
HRM Workflow Execution Engine.
Evaluates workflow definitions against system events and dispatches actions.

Field-name notes (matching actual models):
  WorkflowDefinition.trigger_conditions  (not 'conditions')
  WorkflowExecution.trigger_data         (not 'context')
  WorkflowExecution.tenant               (required FK)
  Notification.recipient / .body / .type (not employee_id / message / notification_type)
"""
import logging
from typing import Any, Optional

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('hrm.workflows')


class WorkflowConditionEvaluator:
    """Evaluates condition rules against an event payload."""

    OPERATORS = {
        'eq':          lambda a, b: a == b,
        'equals':      lambda a, b: a == b,
        'neq':         lambda a, b: a != b,
        'gt':          lambda a, b: float(a) > float(b),
        'gte':         lambda a, b: float(a) >= float(b),
        'lt':          lambda a, b: float(a) < float(b),
        'lte':         lambda a, b: float(a) <= float(b),
        'contains':    lambda a, b: str(b).lower() in str(a).lower(),
        'starts_with': lambda a, b: str(a).lower().startswith(str(b).lower()),
        'in':          lambda a, b: a in (b if isinstance(b, list) else [b]),
    }

    def evaluate(self, conditions: list, context: dict) -> bool:
        """All conditions must pass (AND logic)."""
        for condition in conditions:
            field    = condition.get('field', '')
            operator = condition.get('operator', 'eq')
            value    = condition.get('value')
            actual   = self._get_nested(context, field)
            op_fn    = self.OPERATORS.get(operator)
            if op_fn is None:
                logger.warning(f"Unknown operator: {operator}")
                continue
            try:
                if not op_fn(actual, value):
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def _get_nested(self, obj: dict, path: str) -> Any:
        """Get value from nested dict using dot notation."""
        keys    = path.split('.')
        current = obj
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current


class WorkflowActionDispatcher:
    """Executes workflow actions."""

    def dispatch(self, action: dict, context: dict) -> bool:
        action_type = action.get('type', '')
        # Support legacy 'config' sub-dict
        if 'config' in action and isinstance(action['config'], dict):
            merged = {**action['config'], **action}
            action = merged
        handler = getattr(self, f'_action_{action_type}', None)
        if handler is None:
            logger.warning(f"Unknown workflow action type: {action_type}")
            return False
        try:
            handler(action, context)
            return True
        except Exception as e:
            logger.error(f"Workflow action '{action_type}' failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _action_send_notification(self, action: dict, context: dict):
        """Create an in-app Notification for a user."""
        from platform_core.models import Notification
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Resolve recipient: try employee email → user lookup
        recipient_user = None
        employee_email = context.get('employee_email') or action.get('recipient_email', '')
        user_id = context.get('user_id') or action.get('recipient_user_id')

        if user_id:
            try:
                recipient_user = User.objects.get(pk=user_id)
            except Exception:
                pass

        if recipient_user is None and employee_email:
            try:
                recipient_user = User.objects.get(email=employee_email)
            except Exception:
                pass

        if recipient_user is None:
            logger.warning("send_notification: could not resolve recipient user — skipping")
            return

        message = self._render_template(action.get('message', ''), context)
        tenant_id = context.get('tenant_id')

        notif_kwargs = dict(
            recipient=recipient_user,
            title=action.get('title', 'System Notification'),
            body=message,
            type=action.get('type_level', 'info'),
        )
        if tenant_id:
            notif_kwargs['tenant_id'] = tenant_id

        Notification.objects.create(**notif_kwargs)

    def _action_send_email(self, action: dict, context: dict):
        from platform_core.tasks import send_notification_email
        template_slug    = action.get('template')
        recipient_email  = context.get('employee_email') or action.get('recipient_email')
        if template_slug and recipient_email:
            send_notification_email.delay(
                template_slug=template_slug,
                recipient_email=recipient_email,
                context=context,
            )

    def _action_update_employee_field(self, action: dict, context: dict):
        from core_hr.models import Employee
        employee_id = context.get('employee_id')
        field = action.get('field')
        value = action.get('value')
        if employee_id and field and value is not None:
            try:
                Employee.objects.filter(id=employee_id).update(**{field: value})
            except Exception as e:
                logger.error(f"Failed to update employee field {field}: {e}")

    def _action_update_field(self, action: dict, context: dict):
        """Alias for legacy 'update_field' action type."""
        self._action_update_employee_field(action, context)

    def _action_create_task(self, action: dict, context: dict):
        try:
            from onboarding.models import OnboardingTask
            employee_id = context.get('employee_id')
            if employee_id:
                OnboardingTask.objects.create(
                    title=self._render_template(action.get('title', 'Auto Task'), context),
                    description=action.get('description', ''),
                    category=action.get('category', 'hr'),
                    status='pending',
                )
        except Exception as e:
            logger.warning(f"create_task action failed: {e}")

    def _action_call_webhook(self, action: dict, context: dict):
        from platform_core.webhook_dispatcher import dispatch_webhook
        url = action.get('url')
        if url:
            dispatch_webhook.delay(url=url, payload=context, secret=action.get('secret', ''))

    def _action_create_approval(self, action: dict, context: dict):
        """Create an ApprovalRequest (maps to 'create_approval' action type)."""
        try:
            from platform_core.models import ApprovalRequest
            from django.contrib.auth import get_user_model

            User = get_user_model()
            tenant_id   = context.get('tenant_id')
            employee_id = context.get('employee_id')
            entity_id   = context.get('entity_id', employee_id)

            # ApprovalRequest requires requester + approver User FKs
            requester = None
            if employee_id:
                try:
                    requester = User.objects.filter(employee__id=employee_id).first()
                except Exception:
                    pass

            if requester is None or entity_id is None:
                logger.warning("create_approval: missing requester/entity_id — skipping")
                return

            import uuid as _uuid
            try:
                entity_uuid = _uuid.UUID(str(entity_id))
            except ValueError:
                logger.warning(f"create_approval: entity_id '{entity_id}' is not a valid UUID — skipping")
                return

            create_kwargs = dict(
                requester=requester,
                approver=requester,          # default self-approval; override in action config
                entity_type=action.get('entity_type', 'employee'),
                entity_id=entity_uuid,
                action_type=action.get('approval_type', action.get('action_type', 'general')),
                status='pending',
            )
            if tenant_id:
                create_kwargs['tenant_id'] = tenant_id

            ApprovalRequest.objects.create(**create_kwargs)
        except Exception as e:
            logger.warning(f"create_approval action failed: {e}")

    def _action_create_approval_request(self, action: dict, context: dict):
        """Alias for 'create_approval_request' action type."""
        self._action_create_approval(action, context)

    def _render_template(self, template: str, context: dict) -> str:
        """Simple {{variable}} substitution."""
        result = template
        for key, value in context.items():
            result = result.replace(f'{{{{{key}}}}}', str(value or ''))
        return result


class WorkflowEngine:
    """Main engine: given an event, finds matching workflows and executes them."""

    def __init__(self):
        self.evaluator  = WorkflowConditionEvaluator()
        self.dispatcher = WorkflowActionDispatcher()

    def process_event(self, event_type: str, context: dict, tenant_id=None):
        """
        Called when a system event fires.
        Finds all active WorkflowDefinitions matching event_type (+ tenant),
        evaluates trigger_conditions, and dispatches actions.
        """
        from workflows.models import WorkflowDefinition, WorkflowExecution

        qs = WorkflowDefinition.objects.filter(
            trigger_event=event_type,
            is_active=True,
        )
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        for workflow in qs:
            try:
                conditions = workflow.trigger_conditions or []
                if not self.evaluator.evaluate(conditions, context):
                    continue

                # Enrich context with tenant_id for action handlers
                enriched = {**context}
                if tenant_id:
                    enriched.setdefault('tenant_id', str(tenant_id))

                # Create execution record
                execution = WorkflowExecution.objects.create(
                    tenant_id=workflow.tenant_id,
                    workflow=workflow,
                    trigger_event=event_type,
                    trigger_data=enriched,
                    status='running',
                )

                # Schedule actions (no delay_hours field → always run immediately)
                _execute_workflow_actions.delay(str(execution.id))

                logger.info(
                    f"Workflow '{workflow.name}' triggered by {event_type} "
                    f"(execution #{execution.id})"
                )

            except Exception as e:
                logger.error(f"Workflow processing error for '{workflow.name}': {e}")


_engine = WorkflowEngine()


@shared_task(bind=True, max_retries=3)
def _execute_workflow_actions(self, execution_id: str):
    """Celery task: run all actions for a workflow execution."""
    from workflows.models import WorkflowExecution

    try:
        execution = WorkflowExecution.objects.select_related('workflow').get(id=execution_id)
    except WorkflowExecution.DoesNotExist:
        return

    actions       = execution.workflow.actions or []
    context       = execution.trigger_data or {}
    dispatcher    = WorkflowActionDispatcher()
    success_count = 0
    executed_log  = []

    for action in actions:
        action_type = action.get('type', 'unknown')
        ok = dispatcher.dispatch(action, context)
        if ok:
            success_count += 1
        executed_log.append({
            'action': action_type,
            'status': 'success' if ok else 'failed',
            'timestamp': timezone.now().isoformat(),
        })

    execution.status         = 'completed' if success_count == len(actions) else 'failed'
    execution.actions_executed = executed_log
    execution.completed_at   = timezone.now()
    execution.save(update_fields=['status', 'actions_executed', 'completed_at'])

    logger.info(
        f"Workflow execution #{execution_id} completed: "
        f"{success_count}/{len(actions)} actions succeeded"
    )


def emit_event(event_type: str, context: dict, tenant_id=None):
    """
    Convenience function — call this from signals/views to fire a workflow event.

    Example::

        from workflows.engine import emit_event
        emit_event(
            'leave.approved',
            {'employee_id': emp.id, 'leave_type': 'Annual'},
            tenant_id=emp.tenant_id,
        )
    """
    _process_workflow_event.delay(
        event_type=event_type,
        context=context,
        tenant_id=str(tenant_id) if tenant_id else None,
    )


def fire_event(event_type: str, payload: dict):
    """
    Alias for emit_event using a flat payload dict (compatible with workflow_signals).
    Extracts tenant_id from payload automatically.

    Example::

        from workflows.engine import fire_event
        fire_event('employee.created', {'employee_id': '...', 'tenant_id': '...'})
    """
    tenant_id = payload.get('tenant_id')
    emit_event(event_type, payload, tenant_id=tenant_id)


@shared_task
def _process_workflow_event(event_type: str, context: dict, tenant_id: Optional[str] = None):
    _engine.process_event(event_type, context, tenant_id=tenant_id)
