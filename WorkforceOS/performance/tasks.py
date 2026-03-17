"""Performance module Celery tasks."""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_performance_review_notifications():
    """
    Daily Celery Beat task: notify employees and managers of upcoming
    performance review deadlines (30, 14, 7 days before due date).
    """
    from .models import Review
    from platform_core.email_service import send_notification_email
    from datetime import timedelta

    today = timezone.localdate()
    alert_days = [30, 14, 7]
    sent = 0

    for days in alert_days:
        target_date = today + timedelta(days=days)
        reviews_due = Review.objects.filter(
            due_date=target_date,
            status__in=['pending', 'in_progress'],
        ).select_related('employee', 'reviewer', 'tenant')

        for review in reviews_due:
            employee = review.employee
            reviewer = review.reviewer

            # Notify the reviewer
            if reviewer and reviewer.work_email:
                send_notification_email(
                    template_key='performance_review_due',
                    recipient_email=reviewer.work_email,
                    context={
                        'reviewer_name': reviewer.first_name,
                        'employee_name': employee.full_name if employee else 'Employee',
                        'due_date': target_date.strftime('%Y-%m-%d'),
                        'days_remaining': days,
                        'review_type': review.review_type,
                    },
                    tenant=review.tenant,
                )
                sent += 1

            # Notify the employee (self-assessment)
            if employee and employee.work_email:
                send_notification_email(
                    template_key='performance_self_assessment_due',
                    recipient_email=employee.work_email,
                    context={
                        'employee_name': employee.first_name,
                        'due_date': target_date.strftime('%Y-%m-%d'),
                        'days_remaining': days,
                    },
                    tenant=review.tenant,
                )
                sent += 1

    logger.info("send_performance_review_notifications: sent %d notifications for %s", sent, today)
    return {"sent": sent, "date": str(today)}
