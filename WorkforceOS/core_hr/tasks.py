import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from .models import EmployeeDocument
from platform_core.email_service import send_notification_email

logger = logging.getLogger(__name__)

@shared_task
def check_expiring_documents():
    """
    Daily Celery task to scan for EmployeeDocuments (visas, passports, contracts)
    that expire in exactly 90, 60, 30, or 7 days, and dispatch alert emails.
    """
    today = timezone.localdate()
    # Days before expiry to trigger alerts
    alert_days = [90, 60, 30, 7]
    target_dates = {days: today + timedelta(days=days) for days in alert_days}
    
    alerts_sent = 0

    for days, target_date in target_dates.items():
        # Find documents expiring exactly on target_date for active employees
        expiring_docs = EmployeeDocument.objects.filter(
            expiry_date=target_date, 
            employee__status='active'
        ).select_related('employee', 'tenant')
        
        for doc in expiring_docs:
            employee = doc.employee
            if employee.work_email:
                context = {
                    'employee_name': employee.first_name,
                    'document_title': doc.title,
                    'days_remaining': days,
                    'expiry_date': doc.expiry_date.strftime('%Y-%m-%d')
                }
                
                # Send email via platform core
                success = send_notification_email(
                    template_key='document_expiring',
                    recipient_email=employee.work_email,
                    context=context,
                    tenant=doc.tenant
                )
                if success:
                    alerts_sent += 1
                    
    logger.info(f"check_expiring_documents completed: Sent {alerts_sent} alerts.")
    return alerts_sent


@shared_task
def send_probation_period_alerts():
    """
    Daily Celery Beat task: notify HR managers of employees whose probation period
    ends in exactly 30 or 7 days so they can initiate confirmation/extension actions.
    """
    from .models import Employee
    from platform_core.email_service import send_notification_email

    today = timezone.localdate()
    alert_days = [30, 7]
    sent = 0

    for days in alert_days:
        target_date = today + timedelta(days=days)
        # Employees still on probation whose derived probation end date matches target.
        # probation_end = hire_date + relativedelta(months=probation_months)
        # We cannot filter this in the DB directly, so fetch all probation employees
        # and compare in Python.
        on_probation = [
            emp for emp in Employee.objects.filter(
                status='probation',
                hire_date__isnull=False,
            ).select_related('manager', 'department', 'tenant')
            if emp.hire_date + relativedelta(months=emp.probation_months) == target_date
        ]

        for employee in on_probation:
            # Notify the manager
            manager = employee.manager
            if manager and manager.work_email:
                send_notification_email(
                    template_key='probation_ending',
                    recipient_email=manager.work_email,
                    context={
                        'manager_name': manager.first_name,
                        'employee_name': employee.full_name,
                        'days_remaining': days,
                        'probation_end_date': target_date.strftime('%Y-%m-%d'),
                    },
                    tenant=employee.tenant,
                )
                sent += 1

    logger.info("send_probation_period_alerts: sent %d alerts for %s", sent, today)
    return {"sent": sent, "date": str(today)}
