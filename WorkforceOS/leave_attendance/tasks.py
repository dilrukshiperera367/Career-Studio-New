"""Leave & Attendance Celery tasks — monthly accrual, auto-approval, etc."""

import logging
from datetime import date
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def run_monthly_leave_accrual():
    """
    Run at the end of each month (or daily, checking if today is the last day
    of the month) to accrue entitlement for all eligible employees.

    Logic:
    - For each active LeaveType with accrual_type='monthly', find all active employees.
    - Calculate the monthly accrual increment (annual_days / 12).
    - Get or create the LeaveBalance for the current year.
    - Add the increment to balance (capped at max_carry_forward if configured).
    """
    from .models import LeaveType, LeaveBalance
    from core_hr.models import Employee

    today = date.today()

    # Only accrue on the last day of the month
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    if today.day != last_day:
        logger.debug("run_monthly_leave_accrual: Not the last day of the month. Skipping.")
        return {"skipped": True, "reason": "Not last day of month"}

    accrual_types = LeaveType.objects.filter(
        accrual_type='monthly',
        status='active',
    )

    total_updated = 0

    for leave_type in accrual_types:
        if not leave_type.max_days_per_year:
            continue

        monthly_increment = round(float(leave_type.max_days_per_year) / 12, 4)

        # Find all tenanted active employees
        employees = Employee.objects.filter(
            status__in=['active', 'probation'],
            tenant_id=leave_type.tenant_id,
        )

        for employee in employees:
            balance, created = LeaveBalance.objects.get_or_create(
                tenant_id=leave_type.tenant_id,
                employee=employee,
                leave_type=leave_type,
                year=today.year,
                defaults={
                    'entitled': monthly_increment,
                    'taken': 0,
                    'pending': 0,
                },
            )

            if not created:
                balance.entitled = round(float(balance.entitled) + monthly_increment, 4)

                # Cap at carry-forward limit if set
                max_cf = leave_type.max_carry_forward or None
                if max_cf and balance.entitled > max_cf:
                    balance.entitled = max_cf

                balance.save(update_fields=['entitled'])

            total_updated += 1

    logger.info(
        "run_monthly_leave_accrual: updated %d balances for %s-%s",
        total_updated, today.year, today.month,
    )
    return {"updated": total_updated, "period": f"{today.year}-{today.month:02d}"}


@shared_task
def attendance_auto_clock_out():
    """
    Nightly Celery Beat task (23:50): auto-clock-out any AttendanceRecord
    that was clocked in today but has no clock_out time, preventing open
    attendance records from rolling over to the next day.
    """
    from .models import AttendanceRecord

    today = timezone.localdate()
    midnight = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.max.time().replace(hour=23, minute=59, second=59))
    )

    open_records = AttendanceRecord.objects.filter(
        date=today,
        clock_out__isnull=True,
        clock_in__isnull=False,
    )

    count = open_records.count()
    open_records.update(
        clock_out=midnight,
        notes='Auto clock-out by system (end of day)',
    )

    logger.info("attendance_auto_clock_out: auto-closed %d open records for %s", count, today)
    return {"auto_closed": count, "date": str(today)}
