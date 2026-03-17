"""Celery tasks for Internal Recruiting app."""

from celery import shared_task


@shared_task(name="apps.internal_recruiting.tasks.notify_employees_of_internal_postings")
def notify_employees_of_internal_postings(window_id: str = None):
    """
    Notify all active employees of open internal posting windows.
    If window_id is provided, notify only for that specific window.
    """
    from django.utils import timezone
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.internal_recruiting.models import InternalPostingWindow

    now = timezone.now()

    if window_id:
        windows = InternalPostingWindow.objects.filter(pk=window_id)
    else:
        windows = InternalPostingWindow.objects.filter(
            notify_employees=True,
            notification_sent_at__isnull=True,
            opens_at__lte=now,
            closes_at__gt=now,
        )

    notified = 0
    for window in windows.select_related("job", "tenant"):
        # Get all tenant users (employees) — in production filter by is_active + role
        from apps.accounts.models import User
        employees = User.objects.filter(tenant=window.tenant, is_active=True)
        emails = list(employees.values_list("email", flat=True))

        if emails:
            try:
                send_mail(
                    subject=f"Internal Opportunity: {window.job.title}",
                    message=(
                        f"Hi,\n\nAn internal opportunity has opened: {window.job.title}.\n"
                        f"The internal application window closes on "
                        f"{window.closes_at.strftime('%Y-%m-%d')}.\n\n"
                        f"Log in to your employee portal to apply."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=emails,
                    fail_silently=True,
                )
                notified += len(emails)
            except Exception:
                pass

        if not window_id:
            window.notification_sent_at = now
            window.save(update_fields=["notification_sent_at"])

    return {"employees_notified": notified}


@shared_task(name="apps.internal_recruiting.tasks.close_expired_internal_windows")
def close_expired_internal_windows():
    """
    Close InternalPostingWindows whose closes_at has passed but are still open.
    After closing, their associated job becomes available to external candidates.
    """
    from django.utils import timezone
    from apps.internal_recruiting.models import InternalPostingWindow

    now = timezone.now()
    expired_windows = InternalPostingWindow.objects.filter(
        is_exclusive=True,
        closes_at__lt=now,
    )
    count = expired_windows.count()

    # Mark exclusive flag off so external applications can proceed
    expired_windows.update(is_exclusive=False)

    return {"internal_windows_closed": count}
