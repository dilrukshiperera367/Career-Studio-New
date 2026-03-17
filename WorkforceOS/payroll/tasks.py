"""Payroll Celery tasks — bulk payslip dispatch, certification expiry alerts."""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_payslips(self, payroll_run_id: str):
    """
    Celery task: generate and email payslips for every PayrollEntry
    in a finalized PayrollRun.

    Called as: dispatch_payslips.delay(str(run.id))
    """
    from .models import PayrollRun, PayrollEntry
    from .payslip import generate_payslip_pdf, generate_payslip_html
    from platform_core.email_service import send_notification_email

    try:
        run = PayrollRun.objects.select_related('company').get(id=payroll_run_id)
    except PayrollRun.DoesNotExist:
        logger.error("dispatch_payslips: PayrollRun %s not found", payroll_run_id)
        return {"error": "PayrollRun not found"}

    if run.status != 'finalized':
        logger.warning(
            "dispatch_payslips: Run %s is not finalized (status=%s). Aborting.",
            payroll_run_id, run.status,
        )
        return {"error": f"PayrollRun is in '{run.status}' status; only finalized runs can be dispatched"}

    entries = PayrollEntry.objects.filter(payroll_run=run).select_related('employee')
    sent_count = 0
    failed_count = 0

    for entry in entries:
        employee = entry.employee
        email_address = employee.work_email or employee.personal_email
        if not email_address:
            logger.warning(
                "dispatch_payslips: No email for employee %s (%s) — skipping",
                employee.employee_number, employee.full_name,
            )
            failed_count += 1
            continue

        # Generate payslip as PDF (falls back to HTML if WeasyPrint unavailable)
        try:
            pdf_bytes = generate_payslip_pdf(entry)
            attachment_bytes = pdf_bytes
            attachment_name = f"payslip_{employee.employee_number}_{run.period_year}_{run.period_month:02d}.pdf"
            is_pdf = isinstance(pdf_bytes, bytes) and pdf_bytes[:4] == b'%PDF'
            if not is_pdf:
                attachment_name = attachment_name.replace('.pdf', '.html')
        except Exception as exc:
            logger.error(
                "dispatch_payslips: Failed to generate payslip for %s: %s",
                employee.employee_number, exc,
            )
            failed_count += 1
            continue

        context = {
            'employee_name': employee.first_name,
            'period': f"{run.period_year}-{run.period_month:02d}",
            'company_name': run.company.name if run.company else '',
            'net_salary': float(entry.net_salary),
        }

        try:
            success = send_notification_email(
                template_key='payslip_dispatch',
                recipient_email=email_address,
                context=context,
                tenant=getattr(run, 'tenant', None),
                attachment=attachment_bytes,
                attachment_name=attachment_name,
            )
            if success:
                sent_count += 1
            else:
                failed_count += 1
        except Exception as exc:
            logger.error(
                "dispatch_payslips: Email send failed for %s: %s",
                employee.employee_number, exc,
            )
            # Retry on transient failures
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                failed_count += 1

    logger.info(
        "dispatch_payslips completed for run %s: sent=%d, failed=%d",
        payroll_run_id, sent_count, failed_count,
    )
    return {"sent": sent_count, "failed": failed_count, "total": entries.count()}


@shared_task
def certification_expiry_alerts():
    """
    Daily Celery Beat task: scan for Learning certifications expiring
    in 90 / 60 / 30 / 7 days and email the employee + HR manager.
    """
    from learning.models import Certification
    from platform_core.email_service import send_notification_email

    today = timezone.localdate()
    alert_days = [90, 60, 30, 7]
    alerts_sent = 0

    for days in alert_days:
        target_date = today + timedelta(days=days)
        expiring = Certification.objects.filter(
            expiry_date=target_date,
            employee__status='active',
        ).select_related('employee', 'employee__tenant')

        for cert in expiring:
            employee = cert.employee
            if not employee.work_email:
                continue
            context = {
                'employee_name': employee.first_name,
                'certification_name': cert.name,
                'issuing_body': cert.issuing_body or '',
                'days_remaining': days,
                'expiry_date': cert.expiry_date.strftime('%Y-%m-%d'),
            }
            success = send_notification_email(
                template_key='certification_expiring',
                recipient_email=employee.work_email,
                context=context,
                tenant=getattr(employee, 'tenant', None),
            )
            if success:
                alerts_sent += 1

    logger.info("certification_expiry_alerts: sent %d alerts", alerts_sent)
    return alerts_sent


@shared_task
def arrears_processing(payroll_run_id: str):
    """
    Process salary arrears for a given PayrollRun.
    Arrears arise when a retroactive pay change (promotion/correction)
    was not captured in prior runs.

    Flow:
    1. Find EmployeeCompensation records where effective_from falls before the
       run's period but were updated after the previous run closed.
    2. For each, compare with the prior month's PayrollEntry basic_salary.
    3. If there is a difference, add an Arrears earnings line to the current
       entry (or create one if the entry was already processed).
    """
    from .models import PayrollRun, PayrollEntry, EmployeeCompensation
    from .advanced import process_arrears as calc_arrears
    from datetime import date

    try:
        run = PayrollRun.objects.select_related('company').get(id=payroll_run_id)
    except PayrollRun.DoesNotExist:
        logger.error("arrears_processing: PayrollRun %s not found", payroll_run_id)
        return {"error": "PayrollRun not found"}

    period_date = date(run.period_year, run.period_month, 1)
    count = 0

    # Look for compensation records revised in the last 2 months that
    # are effective before this run's period
    from datetime import timedelta
    cutoff = period_date - timedelta(days=60)

    revised_comps = EmployeeCompensation.objects.filter(
        tenant_id=run.tenant_id,
        employee__company=run.company,
        employee__status__in=['active', 'probation'],
        effective_from__lt=period_date,
        updated_at__gte=cutoff,
        is_current=True,
    ).select_related('employee')

    for comp in revised_comps:
        # Find the prior month's entry for this employee
        prev_year = run.period_year if run.period_month > 1 else run.period_year - 1
        prev_month = run.period_month - 1 if run.period_month > 1 else 12

        prior_entry = PayrollEntry.objects.filter(
            tenant_id=run.tenant_id,
            payroll_run__period_year=prev_year,
            payroll_run__period_month=prev_month,
            employee=comp.employee,
        ).first()

        if not prior_entry:
            continue

        old_salary = float(prior_entry.basic_salary)
        new_salary = float(comp.basic_salary)
        diff = new_salary - old_salary

        if diff <= 0:
            continue  # No arrears if salary went down or unchanged

        # Add arrears to the current run's entry (if it exists)
        current_entry = PayrollEntry.objects.filter(
            tenant_id=run.tenant_id,
            payroll_run=run,
            employee=comp.employee,
        ).first()

        if current_entry:
            earnings = current_entry.earnings_json or []
            # Avoid double-adding
            if not any(e.get('code') == 'ARREARS' for e in earnings):
                earnings.append({
                    'code': 'ARREARS',
                    'name': 'Salary Arrears',
                    'amount': round(diff, 2),
                    'note': f'Backdated adjustment from {comp.effective_from}',
                })
                current_entry.earnings_json = earnings
                current_entry.total_earnings = float(current_entry.total_earnings) + diff
                current_entry.gross_salary = float(current_entry.gross_salary) + diff
                current_entry.net_salary = float(current_entry.net_salary) + diff
                current_entry.save(update_fields=[
                    'earnings_json', 'total_earnings', 'gross_salary', 'net_salary'
                ])
                count += 1

    logger.info(
        "arrears_processing for run %s: processed %d arrears entries",
        payroll_run_id, count,
    )
    return {"count": count, "run_id": payroll_run_id}


@shared_task
def send_payroll_reminders():
    """
    Daily Celery Beat task (day 23 of each month): remind payroll admins to
    initiate payroll processing for the current month before the deadline.
    """
    from django.utils.timezone import localdate
    from platform_core.email_service import send_notification_email
    from tenants.models import Tenant

    today = localdate()
    if today.day != 23:
        logger.debug("send_payroll_reminders: not day 23, skipping.")
        return {"skipped": True}

    tenants = Tenant.objects.filter(status='active')
    sent = 0
    for tenant in tenants:
        # Find payroll admins — users with 'payroll' in their role name
        from authentication.models import User
        admins = User.objects.filter(
            tenant=tenant,
            is_active=True,
            roles__role__name__icontains='payroll',
        ).distinct()
        for admin in admins:
            if not admin.email:
                continue
            success = send_notification_email(
                template_key='payroll_reminder',
                recipient_email=admin.email,
                context={
                    'admin_name': admin.get_full_name() or admin.email,
                    'month': today.strftime('%B %Y'),
                    'deadline_day': 25,
                },
                tenant=tenant,
            )
            if success:
                sent += 1

    logger.info("send_payroll_reminders: sent %d reminders for %s-%02d", sent, today.year, today.month)
    return {"sent": sent, "period": f"{today.year}-{today.month:02d}"}
