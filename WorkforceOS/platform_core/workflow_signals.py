"""
Django signal handlers that fire workflow events.
Connects HRM model saves to the workflow engine.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger('hrm.workflows')


def _fire_safe(event_type: str, payload: dict):
    """Fire workflow event, catching all errors so signals never break normal saves."""
    try:
        from workflows.engine import fire_event
        fire_event(event_type, payload)
    except Exception as e:
        logger.warning(f"Workflow signal failed for {event_type}: {e}")


@receiver(post_save, sender='core_hr.Employee')
def on_employee_created(sender, instance, created, **kwargs):
    if created:
        _fire_safe('employee.created', {
            'employee_id': str(instance.id),
            'employee_name': f"{instance.first_name} {instance.last_name}",
            'employee_email': getattr(instance, 'work_email', '') or '',
            'tenant_id': str(instance.tenant_id),
            'source': getattr(instance, 'source', ''),
        })


@receiver(post_save, sender='leave_attendance.LeaveRequest')
def on_leave_request_status_changed(sender, instance, created, **kwargs):
    if not created and instance.status == 'approved':
        _fire_safe('leave.approved', {
            'employee_id': str(instance.employee_id),
            'leave_type': str(getattr(instance.leave_type, 'name', '')),
            'tenant_id': str(getattr(instance, 'tenant_id', '')),
            'start_date': str(instance.start_date),
            'end_date': str(instance.end_date),
        })
    elif not created and instance.status == 'rejected':
        _fire_safe('leave.rejected', {
            'employee_id': str(instance.employee_id),
            'tenant_id': str(getattr(instance, 'tenant_id', '')),
        })


@receiver(post_save, sender='payroll.PayrollRun')
def on_payroll_finalized(sender, instance, created, **kwargs):
    if not created and instance.status == 'finalized':
        _fire_safe('payroll.finalized', {
            'payroll_run_id': str(instance.id),
            'tenant_id': str(instance.tenant_id),
            'period': str(getattr(instance, 'period_start', '')),
        })
