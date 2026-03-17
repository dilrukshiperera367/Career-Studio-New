"""Celery tasks for Assessments app."""

from celery import shared_task


@shared_task(name="apps.assessments.tasks.send_assessment_reminders")
def send_assessment_reminders():
    """Email candidates with pending/invited assessment orders expiring within 48 hours."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.assessments.models import AssessmentOrder

    now = timezone.now()
    window_end = now + timedelta(hours=48)

    orders = AssessmentOrder.objects.filter(
        status__in=["pending", "invited"],
        expires_at__gte=now,
        expires_at__lte=window_end,
        reminder_sent_at__isnull=True,
    ).select_related("application__candidate", "catalog_item")

    reminded = 0
    for order in orders:
        candidate = order.application.candidate
        # Send reminder email via Django's mail framework
        from django.core.mail import send_mail
        from django.conf import settings

        try:
            send_mail(
                subject=f"Reminder: Complete your {order.catalog_item.name} assessment",
                message=(
                    f"Hi {candidate.full_name},\n\n"
                    f"Your assessment '{order.catalog_item.name}' expires soon. "
                    f"Please complete it before {order.expires_at.strftime('%Y-%m-%d %H:%M UTC')}.\n\n"
                    f"Assessment link: {order.invite_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[candidate.primary_email],
                fail_silently=True,
            )
            order.reminder_sent_at = now
            order.save(update_fields=["reminder_sent_at"])
            reminded += 1
        except Exception:
            pass

    return {"reminders_sent": reminded}


@shared_task(name="apps.assessments.tasks.expire_stale_assessment_orders")
def expire_stale_assessment_orders():
    """Mark assessment orders past their expires_at as expired."""
    from django.utils import timezone
    from apps.assessments.models import AssessmentOrder

    now = timezone.now()
    expired_qs = AssessmentOrder.objects.filter(
        status__in=["pending", "invited", "started"],
        expires_at__lt=now,
    )
    count = expired_qs.count()
    expired_qs.update(status="expired")
    return {"orders_expired": count}
