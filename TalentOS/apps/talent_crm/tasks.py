"""Celery tasks for Talent CRM."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.talent_crm.tasks.send_nurture_sequence_messages")
def send_nurture_sequence_messages():
    """
    Periodic task: send due nurture sequence messages to enrolled prospects/candidates.
    Runs every hour via beat schedule.
    """
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.talent_crm.models import NurtureEnrollment, NurtureStep

    now = timezone.now()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@talentos.io")

    due = NurtureEnrollment.objects.filter(
        status="active",
        next_send_at__lte=now,
    ).select_related("sequence", "prospect", "candidate")

    sent = 0
    for enrollment in due:
        try:
            next_step_num = enrollment.current_step + 1
            step = NurtureStep.objects.filter(
                sequence=enrollment.sequence,
                step_number=next_step_num,
            ).first()

            if not step:
                enrollment.status = "completed"
                enrollment.save(update_fields=["status"])
                continue

            # Resolve recipient email
            if enrollment.prospect:
                email = enrollment.prospect.email
                name = f"{enrollment.prospect.first_name} {enrollment.prospect.last_name}".strip()
            elif enrollment.candidate:
                email = getattr(enrollment.candidate, "primary_email", "") or getattr(enrollment.candidate, "email", "")
                name = f"{getattr(enrollment.candidate, 'first_name', '')} {getattr(enrollment.candidate, 'last_name', '')}".strip()
            else:
                enrollment.status = "completed"
                enrollment.save(update_fields=["status"])
                continue

            if not email:
                continue

            body = step.body_template.replace("{{name}}", name)
            subject = step.subject_line.replace("{{name}}", name)

            send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=[email],
                fail_silently=True,
            )

            # Schedule next step
            next_next_step = NurtureStep.objects.filter(
                sequence=enrollment.sequence,
                step_number=next_step_num + 1,
            ).first()

            enrollment.current_step = next_step_num
            enrollment.last_sent_at = now
            if next_next_step:
                enrollment.next_send_at = now + timezone.timedelta(days=next_next_step.delay_days)
            else:
                enrollment.status = "completed"
                enrollment.next_send_at = None
            enrollment.save(update_fields=[
                "current_step", "last_sent_at", "next_send_at", "status"
            ])
            sent += 1

        except Exception as exc:
            logger.error("nurture send failed for enrollment %s: %s", enrollment.id, exc)

    logger.info("send_nurture_sequence_messages: %d messages sent", sent)
    return {"sent": sent}


@shared_task(name="apps.talent_crm.tasks.mark_dormant_prospects")
def mark_dormant_prospects():
    """
    Weekly task: mark prospects that have not been contacted in 90+ days as dormant.
    """
    from apps.talent_crm.models import Prospect

    cutoff = timezone.now() - timezone.timedelta(days=90)
    updated = Prospect.objects.filter(
        status__in=["new", "contacted", "engaged"],
        last_contacted_at__lte=cutoff,
    ).update(status="dormant")

    logger.info("mark_dormant_prospects: %d prospects marked dormant", updated)
    return {"marked_dormant": updated}


@shared_task(name="apps.talent_crm.tasks.expire_do_not_contact_records")
def expire_do_not_contact_records():
    """
    Daily task: remove DNC records whose expiry_date has passed.
    """
    from apps.talent_crm.models import DoNotContact

    now = timezone.now()
    deleted_count, _ = DoNotContact.objects.filter(
        expires_at__lte=now,
    ).delete()

    logger.info("expire_do_not_contact_records: %d records removed", deleted_count)
    return {"deleted": deleted_count}
