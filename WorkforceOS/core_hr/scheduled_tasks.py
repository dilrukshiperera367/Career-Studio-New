"""
Additional HRM Celery tasks for audit items #151–#156.

Tasks:
  #151 - attendance_auto_clock_out       — clock out employees who forgot
  #153 - send_payroll_reminders          — notify managers before payroll cutoff
  #154 - send_performance_review_notifications — remind reviewers of upcoming reviews
  #155 - send_onboarding_task_reminders  — remind new hires of pending onboarding tasks
  #156 - send_probation_period_alerts    — alert HR before probation end dates
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger("hrm.tasks")


# ---------------------------------------------------------------------------
# #151 — Auto clock-out employees who are still clocked in at end of shift
# ---------------------------------------------------------------------------

@shared_task(name="leave_attendance.tasks.attendance_auto_clock_out")
def attendance_auto_clock_out():
    """
    Runs nightly.  Finds any open attendance records (no clock-out) from the
    previous business day and auto-closes them at midnight, flagging them
    as auto-closed.
    """
    from django.utils import timezone as tz

    yesterday = tz.localdate() - timedelta(days=1)

    try:
        from leave_attendance.models import AttendanceRecord
    except ImportError:
        logger.warning("attendance_auto_clock_out: AttendanceRecord model not found")
        return {"closed": 0}

    open_records = AttendanceRecord.objects.filter(
        check_in__date__lte=yesterday,
        check_out__isnull=True,
    )

    closed = 0
    for record in open_records:
        # Set check-out to end of that work day (midnight)
        record.check_out = tz.datetime.combine(
            record.check_in.date(),
            tz.datetime.max.time().replace(hour=23, minute=59, second=59),
            tzinfo=tz.utc,
        )
        # Mark as auto-closed if the field exists
        if hasattr(record, "auto_closed"):
            record.auto_closed = True
        if hasattr(record, "notes"):
            record.notes = (record.notes or "") + " [auto closed by system]"
        update_fields = ["check_out"]
        if hasattr(record, "auto_closed"):
            update_fields.append("auto_closed")
        if hasattr(record, "notes"):
            update_fields.append("notes")
        record.save(update_fields=update_fields)
        closed += 1

    logger.info("attendance_auto_clock_out: %d records closed", closed)
    return {"closed": closed}


# ---------------------------------------------------------------------------
# #153 — Payroll reminders before cutoff date
# ---------------------------------------------------------------------------

@shared_task(name="payroll.tasks.send_payroll_reminders")
def send_payroll_reminders():
    """
    Runs on the 23rd of each month.  Warns payroll managers that the
    payroll cutoff is approaching (typically end of month).
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        from authentication.models import User
        from tenants.models import Tenant
    except ImportError:
        logger.warning("send_payroll_reminders: models not available")
        return {"sent": 0}

    today = timezone.localdate()
    # Only send on the 23rd or if explicitly called
    if today.day != 23:
        return {"skipped": True, "reason": f"Not payroll reminder day (day={today.day})"}

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@connectos.io")
    sent = 0

    for tenant in Tenant.objects.filter(status="active"):
        payroll_managers = User.objects.filter(
            tenant=tenant,
            is_active=True,
        ).filter(
            groups__name__icontains="payroll",
        )
        if not payroll_managers.exists():
            # Fall back to admins
            payroll_managers = User.objects.filter(
                tenant=tenant,
                is_superuser=True,
                is_active=True,
            )

        for user in payroll_managers:
            try:
                send_mail(
                    subject=f"[{tenant.name}] Payroll Cutoff Reminder — {today.strftime('%B %Y')}",
                    message=(
                        f"Hi {user.first_name or 'there'},\n\n"
                        f"This is a reminder that the {today.strftime('%B')} payroll cutoff is approaching.\n\n"
                        "Please ensure all timesheets, leave records, and salary adjustments are finalised "
                        "before the end of this month.\n\n"
                        "ConnectHRM"
                    ),
                    from_email=from_email,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                sent += 1
            except Exception as exc:
                logger.warning("payroll_reminder email failed: %s", exc)

    logger.info("send_payroll_reminders: %d emails sent", sent)
    return {"sent": sent}


# ---------------------------------------------------------------------------
# #154 — Performance review cycle notifications
# ---------------------------------------------------------------------------

@shared_task(name="performance.tasks.send_performance_review_notifications")
def send_performance_review_notifications():
    """
    Daily task: find upcoming performance review cycles that start within
    the next 7 days and notify reviewers / reviewees.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        from performance.models import ReviewCycle
    except ImportError:
        logger.warning("send_performance_review_notifications: ReviewCycle not found")
        return {"sent": 0}

    today = timezone.localdate()
    window_start = today
    window_end = today + timedelta(days=7)

    upcoming = ReviewCycle.objects.filter(
        start_date__range=(window_start, window_end),
        status="scheduled",
    ).select_related("tenant")

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@connectos.io")
    sent = 0

    for cycle in upcoming:
        days_until = (cycle.start_date - today).days
        # Notify manager/HR
        try:
            from authentication.models import User
            admins = User.objects.filter(
                tenant=cycle.tenant,
                is_active=True,
                is_superuser=True,
            )
            for admin in admins:
                send_mail(
                    subject=f"Performance Review Cycle '{cycle.name}' starts in {days_until} day(s)",
                    message=(
                        f"Hi {admin.first_name or 'there'},\n\n"
                        f"The '{cycle.name}' performance review cycle begins on "
                        f"{cycle.start_date.strftime('%d %B %Y')}.\n\n"
                        "Please ensure all employees are enrolled and managers are notified.\n\n"
                        "ConnectHRM"
                    ),
                    from_email=from_email,
                    recipient_list=[admin.email],
                    fail_silently=True,
                )
                sent += 1
        except Exception as exc:
            logger.warning("performance review notification failed: %s", exc)

    logger.info("send_performance_review_notifications: %d notifications sent", sent)
    return {"sent": sent}


# ---------------------------------------------------------------------------
# #155 — Onboarding task reminders for new hires
# ---------------------------------------------------------------------------

@shared_task(name="onboarding.tasks.send_onboarding_task_reminders")
def send_onboarding_task_reminders():
    """
    Daily task: remind new hires (and their buddies/managers) of pending
    onboarding tasks that are due within the next 2 days.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        from onboarding.models import OnboardingTask, OnboardingAssignment
    except ImportError:
        logger.warning("send_onboarding_task_reminders: Onboarding models not found")
        return {"sent": 0}

    today = timezone.localdate()
    deadline = today + timedelta(days=2)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@connectos.io")
    sent = 0

    overdue_tasks = OnboardingTask.objects.filter(
        due_date__lte=deadline,
        status__in=["pending", "in_progress"],
    ).select_related("employee", "tenant")

    for task in overdue_tasks:
        emp = task.employee
        if not emp:
            continue
        email = getattr(emp, "work_email", None) or getattr(emp, "personal_email", None)
        if not email:
            continue
        days_left = (task.due_date - today).days if task.due_date else None
        try:
            send_mail(
                subject=f"Onboarding Task Reminder: {task.title}",
                message=(
                    f"Hi {emp.first_name},\n\n"
                    f"Please complete your onboarding task: '{task.title}'.\n"
                    + (f"Due in {days_left} day(s).\n\n" if days_left is not None else "\n")
                    + "Log in to ConnectHRM to complete it.\n\nConnectHRM Onboarding"
                ),
                from_email=from_email,
                recipient_list=[email],
                fail_silently=True,
            )
            sent += 1
        except Exception as exc:
            logger.warning("onboarding reminder failed for %s: %s", emp.id, exc)

    logger.info("send_onboarding_task_reminders: %d reminders sent", sent)
    return {"sent": sent}


# ---------------------------------------------------------------------------
# #156 — Probation period alerts (14-day and 7-day warnings)
# ---------------------------------------------------------------------------

@shared_task(name="core_hr.tasks.send_probation_period_alerts")
def send_probation_period_alerts():
    """
    Daily task: alert HR managers when an employee's probation end date is
    coming up in 14 or 7 days.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        from core_hr.models import Employee
        from authentication.models import User
    except ImportError:
        logger.warning("send_probation_period_alerts: models not found")
        return {"sent": 0}

    today = timezone.localdate()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@connectos.io")
    sent = 0

    for days_ahead in [14, 7]:
        target_date = today + timedelta(days=days_ahead)
        employees = Employee.objects.filter(
            probation_end_date=target_date,
            status="probation",
        ).select_related("tenant")

        for emp in employees:
            # Notify HR/admin users for this tenant
            hr_users = User.objects.filter(
                tenant=emp.tenant,
                is_active=True,
                is_superuser=True,
            )
            for hr in hr_users:
                try:
                    send_mail(
                        subject=f"Probation Review Due: {emp.first_name} {emp.last_name} ({days_ahead} days)",
                        message=(
                            f"Hi {hr.first_name or 'HR Team'},\n\n"
                            f"{emp.first_name} {emp.last_name}'s probation period ends on "
                            f"{emp.probation_end_date.strftime('%d %B %Y')} ({days_ahead} days).\n\n"
                            "Please schedule and complete the probation review before that date.\n\n"
                            "ConnectHRM"
                        ),
                        from_email=from_email,
                        recipient_list=[hr.email],
                        fail_silently=True,
                    )
                    sent += 1
                except Exception as exc:
                    logger.warning("probation alert failed: %s", exc)

    logger.info("send_probation_period_alerts: %d alerts sent", sent)
    return {"sent": sent}
