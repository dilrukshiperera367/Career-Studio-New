"""Onboarding module Celery tasks."""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_onboarding_task_reminders():
    """
    Daily Celery Beat task: remind new hires (and their onboarding buddies/managers)
    of onboarding tasks that are due in 3 days or overdue.
    """
    from .models import OnboardingTask
    from platform_core.email_service import send_notification_email
    from datetime import timedelta

    today = timezone.localdate()
    due_soon = today + timedelta(days=3)
    sent = 0

    # Tasks due in 3 days — send a heads-up
    upcoming = OnboardingTask.objects.filter(
        due_date=due_soon,
        status__in=['pending', 'in_progress'],
    ).select_related('instance__employee', 'instance__employee__tenant', 'assignee')

    for task in upcoming:
        employee = task.instance.employee if task.instance else None
        if not employee:
            continue
        recipients = []
        if employee.work_email:
            recipients.append(employee.work_email)
        if task.assignee and task.assignee.email and task.assignee.email not in recipients:
            recipients.append(task.assignee.email)
        for email in recipients:
            send_notification_email(
                template_key='onboarding_task_due_soon',
                recipient_email=email,
                context={
                    'employee_name': employee.full_name,
                    'task_title': task.title,
                    'due_date': due_soon.strftime('%Y-%m-%d'),
                    'days_remaining': 3,
                },
                tenant=employee.tenant,
            )
            sent += 1

    # Overdue tasks — send an escalation reminder
    overdue = OnboardingTask.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'in_progress'],
    ).select_related('instance__employee', 'instance__employee__tenant', 'assignee')

    for task in overdue:
        employee = task.instance.employee if task.instance else None
        if not employee or not employee.work_email:
            continue
        send_notification_email(
            template_key='onboarding_task_overdue',
            recipient_email=employee.work_email,
            context={
                'employee_name': employee.full_name,
                'task_title': task.title,
                'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else 'N/A',
            },
            tenant=employee.tenant,
        )
        sent += 1

    logger.info("send_onboarding_task_reminders: sent %d reminders for %s", sent, today)
    return {"sent": sent, "date": str(today)}
