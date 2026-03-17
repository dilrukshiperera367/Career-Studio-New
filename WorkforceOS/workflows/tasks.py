"""Celery tasks for HRM workflow engine."""
import logging
from celery import shared_task

logger = logging.getLogger('hrm.workflows')


@shared_task(bind=True, max_retries=3)
def execute_delayed_action(self, action: dict, payload: dict, execution_id: str = None):
    """Execute a workflow action that was delayed by delay_hours."""
    from workflows.engine import WorkflowActionDispatcher
    dispatcher = WorkflowActionDispatcher()
    try:
        ok = dispatcher.dispatch(action, payload)
        if not ok:
            raise RuntimeError(f"Action dispatch returned False for {action.get('type')}")
    except Exception as exc:
        logger.error(f"Delayed action failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def process_due_workflow_events():
    """
    Periodically scan for events that need workflow processing.
    Called by Celery Beat every 5 minutes.
    """
    from workflows.engine import fire_event
    from django.utils import timezone
    from datetime import timedelta

    # Check for probation review due
    try:
        from core_hr.models import Employee
        due_date = timezone.now().date() + timedelta(days=14)
        probation_due = Employee.objects.filter(
            probation_end_date=due_date,
            status='probation',
        ).select_related('tenant')
        for emp in probation_due:
            fire_event('probation.review_due', {
                'employee_id': str(emp.id),
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'employee_email': getattr(emp, 'work_email', '') or getattr(emp, 'email', ''),
                'tenant_id': str(emp.tenant_id),
                'probation_end_date': str(due_date),
            })
    except Exception as e:
        logger.error(f"Probation review check failed: {e}")

    # Check for contract expiry 30 days ahead
    try:
        from core_hr.models import Employee
        expiry_date = timezone.now().date() + timedelta(days=30)
        contracts_expiring = Employee.objects.filter(
            contract_end_date=expiry_date,
            status='active',
        ).select_related('tenant')
        for emp in contracts_expiring:
            fire_event('contract.expiry_warning', {
                'employee_id': str(emp.id),
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'employee_email': getattr(emp, 'work_email', '') or getattr(emp, 'email', ''),
                'tenant_id': str(emp.tenant_id),
                'contract_end_date': str(expiry_date),
            })
    except Exception as e:
        logger.error(f"Contract expiry check failed: {e}")

    logger.info("Workflow due-events scan complete")


@shared_task
def send_work_anniversary_greetings():
    """Fire anniversary events for employees with work anniversaries today."""
    from django.utils import timezone
    today = timezone.now().date()
    try:
        from core_hr.models import Employee
        from workflows.engine import fire_event
        anniversaries = Employee.objects.filter(
            hire_date__month=today.month,
            hire_date__day=today.day,
            status='active',
        ).exclude(hire_date__year=today.year)  # Exclude first-day hires
        count = 0
        for emp in anniversaries:
            years = today.year - emp.hire_date.year
            fire_event('employee.anniversary', {
                'employee_id': str(emp.id),
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'employee_email': getattr(emp, 'work_email', '') or getattr(emp, 'email', ''),
                'tenant_id': str(emp.tenant_id),
                'years': years,
            })
            count += 1
        logger.info(f"Sent {count} anniversary greetings")
    except Exception as e:
        logger.error(f"Anniversary greeting task failed: {e}")


@shared_task
def send_birthday_greetings():
    """Fire birthday events for employees with birthdays today."""
    from django.utils import timezone
    today = timezone.now().date()
    try:
        from core_hr.models import Employee
        from workflows.engine import fire_event
        birthdays = Employee.objects.filter(
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
            status='active',
        )
        count = 0
        for emp in birthdays:
            fire_event('employee.birthday', {
                'employee_id': str(emp.id),
                'employee_name': f"{emp.first_name} {emp.last_name}",
                'employee_email': getattr(emp, 'work_email', '') or getattr(emp, 'email', ''),
                'tenant_id': str(emp.tenant_id),
            })
            count += 1
        logger.info(f"Sent {count} birthday greetings")
    except Exception as e:
        logger.error(f"Birthday greeting task failed: {e}")
