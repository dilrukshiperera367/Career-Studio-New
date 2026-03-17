"""
Workflow Engine — Event-driven automation with idempotent execution.

Handles: stage_changed, application_created, application_idle, etc.
Evaluates automation rules per tenant and dispatches actions idempotently.
"""

import hashlib
import logging
import uuid
from typing import Optional

from django.db import IntegrityError
from apps.workflows.models import AutomationRule, WorkflowExecution, IdempotencyKey

logger = logging.getLogger(__name__)


def process_event(event_data: dict):
    """
    Process a workflow trigger event.

    event_data: {
        "tenant_id": "...",
        "event_type": "stage_changed",
        "event_id": "...",
        "payload": {
            "application_id": "...",
            "from_stage_type": "applied",
            "to_stage_type": "screening",
            "candidate_id": "...",
            "job_id": "...",
        }
    }
    """
    tenant_id = event_data.get("tenant_id")
    event_type = event_data.get("event_type")
    event_id = event_data.get("event_id", str(uuid.uuid4()))
    payload = event_data.get("payload", {})

    # Find matching rules
    rules = AutomationRule.objects.filter(
        tenant_id=tenant_id,
        trigger_type=event_type,
        enabled=True,
    )

    for rule in rules:
        if _conditions_match(rule.conditions_json, payload):
            for action in rule.actions_json:
                _execute_action_idempotent(
                    tenant_id=tenant_id,
                    rule=rule,
                    event_id=event_id,
                    action=action,
                    payload=payload,
                )


def _conditions_match(conditions: dict, payload: dict) -> bool:
    """Evaluate if payload matches rule conditions."""
    if not conditions:
        return True

    for key, expected in conditions.items():
        actual = payload.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False

    return True


def _execute_action_idempotent(
    tenant_id: str,
    rule: AutomationRule,
    event_id: str,
    action: dict,
    payload: dict,
):
    """Execute an action with idempotency checking."""
    action_type = action.get("type", "unknown")
    target = action.get("template_id", action.get("target", ""))

    # Compute idempotency key: sha256(tenant + event + action_type + target)
    key_material = f"{tenant_id}:{event_id}:{action_type}:{target}"
    idem_key = hashlib.sha256(key_material.encode()).hexdigest()

    # Check/create idempotency key
    try:
        IdempotencyKey.objects.create(
            tenant_id=tenant_id,
            key=idem_key,
        )
    except IntegrityError:
        logger.info(f"Action already executed (idempotent skip): {idem_key}")
        WorkflowExecution.objects.create(
            tenant_id=tenant_id,
            rule=rule,
            event_id=event_id,
            action_type=action_type,
            action_target=str(target),
            status="skipped",
        )
        return

    # Dispatch action
    try:
        if action_type == "send_email":
            _dispatch_send_email(tenant_id, action, payload)
        elif action_type == "move_stage":
            _dispatch_move_stage(tenant_id, action, payload)
        elif action_type == "assign_tag":
            _dispatch_assign_tag(tenant_id, action, payload)
        elif action_type == "notify_user":
            _dispatch_notify_user(tenant_id, action, payload)
        elif action_type == "update_candidate":
            _dispatch_update_candidate(tenant_id, action, payload)
        elif action_type == "assign_recruiter":
            _dispatch_assign_recruiter(tenant_id, action, payload)
        elif action_type == "schedule_interview":
            _dispatch_schedule_interview(tenant_id, action, payload)
        elif action_type == "create_task":
            _dispatch_create_task(tenant_id, action, payload)
        elif action_type == "escalate":
            _dispatch_escalate(tenant_id, action, payload)
        else:
            logger.warning(f"Unknown action type: {action_type}")

        WorkflowExecution.objects.create(
            tenant_id=tenant_id,
            rule=rule,
            event_id=event_id,
            action_type=action_type,
            action_target=str(target),
            status="success",
        )

    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        WorkflowExecution.objects.create(
            tenant_id=tenant_id,
            rule=rule,
            event_id=event_id,
            action_type=action_type,
            action_target=str(target),
            status="failed",
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Action dispatchers
# ---------------------------------------------------------------------------

def _dispatch_send_email(tenant_id: str, action: dict, payload: dict):
    """Queue an email via the messaging service."""
    from apps.messaging.services import queue_email

    template_id = action.get("template_id")
    candidate_id = payload.get("candidate_id")
    application_id = payload.get("application_id")

    queue_email(
        tenant_id=tenant_id,
        template_slug=template_id,
        candidate_id=candidate_id,
        application_id=application_id,
        context=payload,
    )


def _dispatch_move_stage(tenant_id: str, action: dict, payload: dict):
    """Auto-move application to next stage."""
    from apps.applications.models import Application
    from apps.jobs.models import PipelineStage

    application_id = payload.get("application_id")
    target_stage_type = action.get("target_stage_type")

    try:
        app = Application.objects.get(id=application_id, tenant_id=tenant_id)
        target_stage = PipelineStage.objects.filter(
            job=app.job, stage_type=target_stage_type, tenant_id=tenant_id,
        ).first()
        if target_stage:
            app.current_stage = target_stage
            app.save(update_fields=["current_stage", "updated_at"])
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found")


def _dispatch_assign_tag(tenant_id: str, action: dict, payload: dict):
    """Add tag to application."""
    from apps.applications.models import Application

    application_id = payload.get("application_id")
    tag = action.get("tag", "")

    try:
        app = Application.objects.get(id=application_id, tenant_id=tenant_id)
        if tag and tag not in app.tags:
            app.tags.append(tag)
            app.save(update_fields=["tags", "updated_at"])
    except Application.DoesNotExist:
        pass


def _dispatch_notify_user(tenant_id: str, action: dict, payload: dict):
    """Create in-app notification."""
    from apps.accounts.models import Notification

    user_id = action.get("user_id") or payload.get("assigned_to_id")
    if not user_id:
        logger.warning("notify_user action: no user_id specified")
        return

    Notification.objects.create(
        tenant_id=tenant_id,
        user_id=user_id,
        notification_type=action.get("notification_type", "workflow"),
        title=action.get("title", "Workflow Notification"),
        body=action.get("body", "An automated workflow triggered this notification."),
        entity_type=action.get("entity_type", "application"),
        entity_id=payload.get("application_id", ""),
    )
    logger.info(f"Notification created for user {user_id}")


def _dispatch_update_candidate(tenant_id: str, action: dict, payload: dict):
    """Update candidate fields (e.g. pool_status, talent_tier)."""
    from apps.candidates.models import Candidate

    candidate_id = payload.get("candidate_id")
    if not candidate_id:
        return

    try:
        candidate = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
        update_fields = []
        if "pool_status" in action:
            candidate.pool_status = action["pool_status"]
            update_fields.append("pool_status")
        if "talent_tier" in action:
            candidate.talent_tier = action["talent_tier"]
            update_fields.append("talent_tier")
        if "tags" in action:
            candidate.tags = list(set((candidate.tags or []) + action["tags"]))
            update_fields.append("tags")
        if update_fields:
            update_fields.append("updated_at")
            candidate.save(update_fields=update_fields)
    except Exception as e:
        logger.error(f"Update candidate failed: {e}")


def _dispatch_assign_recruiter(tenant_id: str, action: dict, payload: dict):
    """Auto-assign a recruiter to an application."""
    from apps.applications.models import Application

    application_id = payload.get("application_id")
    recruiter_id = action.get("recruiter_id")
    if not application_id or not recruiter_id:
        return

    try:
        app = Application.objects.get(id=application_id, tenant_id=tenant_id)
        app.assigned_recruiter_id = recruiter_id
        app.save(update_fields=["assigned_recruiter", "updated_at"])
    except Application.DoesNotExist:
        pass


def _dispatch_schedule_interview(tenant_id: str, action: dict, payload: dict):
    """Auto-create an interview placeholder."""
    from apps.applications.models import Interview

    application_id = payload.get("application_id")
    candidate_id = payload.get("candidate_id")
    job_id = payload.get("job_id")

    if not all([application_id, candidate_id, job_id]):
        return

    Interview.objects.create(
        tenant_id=tenant_id,
        application_id=application_id,
        candidate_id=candidate_id,
        job_id=job_id,
        interview_type=action.get("interview_type", "phone_screen"),
        interviewer_name=action.get("interviewer_name", "To Be Assigned"),
        round_number=action.get("round_number", 1),
        round_name=action.get("round_name", "Auto-Scheduled"),
        status="pending",
    )


def _dispatch_create_task(tenant_id: str, action: dict, payload: dict):
    """Create an onboarding task for an employee."""
    from apps.applications.models import Employee, OnboardingTask

    candidate_id = payload.get("candidate_id")
    if not candidate_id:
        return

    try:
        employee = Employee.objects.get(candidate_id=candidate_id, tenant_id=tenant_id)
        OnboardingTask.objects.create(
            tenant_id=tenant_id,
            employee=employee,
            title=action.get("title", "Auto-created task"),
            description=action.get("description", ""),
            category=action.get("category", "admin"),
        )
    except Employee.DoesNotExist:
        logger.warning(f"No employee for candidate {candidate_id}")


def _dispatch_escalate(tenant_id: str, action: dict, payload: dict):
    """Escalation chain: recruiter → manager → director."""
    from apps.accounts.models import Notification, User

    # Determine escalation level from action config
    level = action.get("level", "manager")  # recruiter, manager, director

    # Find target users by role
    role_map = {
        "recruiter": "recruiter",
        "manager": "hiring_manager",
        "director": "admin",
    }
    target_role = role_map.get(level, "admin")

    targets = User.objects.filter(
        tenant_id=tenant_id,
        user_type=target_role,
        is_active=True,
    )[:5]  # Cap to avoid spam

    for user in targets:
        Notification.objects.create(
            tenant_id=tenant_id,
            user=user,
            notification_type="escalation",
            title=action.get("title", f"Escalation: Action Required"),
            body=action.get("body", f"An item requires your attention (escalated from {level})."),
            entity_type=payload.get("entity_type", "application"),
            entity_id=payload.get("application_id", ""),
        )

    logger.info(f"Escalated to {targets.count()} {target_role}(s)")


# ---------------------------------------------------------------------------
# Multi-Step Workflow Execution (Features 79-88)
# ---------------------------------------------------------------------------

def process_multi_step_workflow(tenant_id: str, rule_id: str, event_data: dict):
    """
    Execute a multi-step workflow with delays and conditional branching.
    Uses the WorkflowStep model for step definitions.
    """
    from apps.workflows.models import WorkflowStep

    steps = WorkflowStep.objects.filter(
        rule_id=rule_id,
    ).order_by("order")

    payload = event_data.get("payload", {})
    event_id = event_data.get("event_id", str(uuid.uuid4()))

    for step in steps:
        # Check conditions
        if step.condition_json and not _evaluate_step_conditions(step.condition_json, payload):
            logger.info(f"Step {step.order} skipped: conditions not met")
            continue

        # Check if delayed
        if step.delay_hours and step.delay_hours > 0:
            # Schedule for later execution
            from django.utils import timezone
            import datetime
            execute_at = timezone.now() + datetime.timedelta(hours=step.delay_hours)
            WorkflowExecution.objects.create(
                tenant_id=tenant_id,
                rule_id=rule_id,
                step=step,
                event_id=event_id,
                action_type=step.action_type,
                action_target=str(step.action_config),
                status="pending",
                execute_at=execute_at,
            )
            logger.info(f"Step {step.order} scheduled for {execute_at}")
            continue

        # Execute immediately
        action = {
            "type": step.action_type,
            **step.action_config,
        }

        try:
            rule = AutomationRule.objects.get(id=rule_id)
            _execute_action_idempotent(
                tenant_id=tenant_id,
                rule=rule,
                event_id=f"{event_id}-step-{step.order}",
                action=action,
                payload=payload,
            )
        except AutomationRule.DoesNotExist:
            logger.error(f"Rule {rule_id} not found")


def _evaluate_step_conditions(conditions: dict, payload: dict) -> bool:
    """
    Evaluate step conditions with operators.

    Supports:
    - "equals": {"field": "value"}
    - "not_equals": {"field": "value"}
    - "contains": {"field": "value"}
    - "gt": {"field": value}   (greater than)
    - "lt": {"field": value}   (less than)
    """
    for op, checks in conditions.items():
        if not isinstance(checks, dict):
            continue
        for field, expected in checks.items():
            actual = payload.get(field)
            if op == "equals" and actual != expected:
                return False
            elif op == "not_equals" and actual == expected:
                return False
            elif op == "contains" and (not actual or expected not in str(actual)):
                return False
            elif op == "gt" and (actual is None or actual <= expected):
                return False
            elif op == "lt" and (actual is None or actual >= expected):
                return False
    return True


def execute_pending_workflow_steps():
    """
    Execute workflow steps that are pending and past their execute_at time.
    Called by a periodic Celery task.
    """
    from django.utils import timezone

    pending = WorkflowExecution.objects.filter(
        status="pending",
        execute_at__lte=timezone.now(),
    ).select_related("rule", "step")

    executed = 0
    for execution in pending:
        if not execution.step:
            execution.status = "skipped"
            execution.save(update_fields=["status"])
            continue

        action = {
            "type": execution.step.action_type,
            **execution.step.action_config,
        }

        try:
            dispatch_map = {
                "send_email": _dispatch_send_email,
                "move_stage": _dispatch_move_stage,
                "assign_tag": _dispatch_assign_tag,
                "notify_user": _dispatch_notify_user,
                "update_candidate": _dispatch_update_candidate,
                "assign_recruiter": _dispatch_assign_recruiter,
                "schedule_interview": _dispatch_schedule_interview,
                "create_task": _dispatch_create_task,
                "escalate": _dispatch_escalate,
            }

            handler = dispatch_map.get(action["type"])
            if handler:
                handler(execution.tenant_id, action, {"application_id": execution.action_target})
                execution.status = "success"
            else:
                execution.status = "skipped"
                execution.error = f"Unknown action type: {action['type']}"

        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)

        execution.save(update_fields=["status", "error"])
        executed += 1

    logger.info(f"Executed {executed} pending workflow steps")
    return executed
