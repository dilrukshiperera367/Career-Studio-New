"""
Celery tasks for ATS job lifecycle management.

Tasks:
  - auto_close_stale_jobs     (#58) — close jobs past their deadline
  - send_interview_reminders  (#59) — 24h and 1h reminder emails
  - enforce_candidate_retention (#61) — delete/anonymise stale candidate data
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# #58 — Auto-close stale / deadline-expired jobs
# ---------------------------------------------------------------------------

@shared_task(name="apps.jobs.tasks.auto_close_stale_jobs")
def auto_close_stale_jobs():
    """
    Daily task: automatically close open jobs whose `application_deadline`
    has passed, and jobs that have been open for more than the tenant's
    configured max-open-days (default 90).
    """
    from apps.jobs.models import Job
    from apps.tenants.models import TenantSettings

    now = timezone.now()

    # 1) Close jobs whose application deadline has passed
    deadline_expired = Job.objects.filter(
        status="open",
        application_deadline__lte=now,
    )
    deadline_count = 0
    for job in deadline_expired:
        job.status = "closed"
        job.closed_at = now
        job.save(update_fields=["status", "closed_at"])
        # Fire workflow event in case automations are hooked here
        try:
            from apps.workflows.services import process_event
            process_event({
                "tenant_id": str(job.tenant_id),
                "event_type": "job_closed",
                "event_id": f"auto-close-deadline-{job.id}",
                "payload": {"job_id": str(job.id), "reason": "deadline_expired"},
            })
        except Exception:
            pass
        deadline_count += 1

    # 2) Close jobs that have been open > max_open_days (per-tenant config, default 90)
    stale_count = 0
    from apps.tenants.models import Tenant
    for tenant in Tenant.objects.filter(status="active"):
        settings_obj = TenantSettings.objects.filter(tenant=tenant).first()
        max_days = getattr(settings_obj, "max_job_open_days", 90)
        cutoff = now - timezone.timedelta(days=max_days)

        stale_jobs = Job.objects.filter(
            tenant=tenant,
            status="open",
            published_at__lte=cutoff,
            application_deadline__isnull=True,  # already handled above
        )
        for job in stale_jobs:
            job.status = "closed"
            job.closed_at = now
            job.save(update_fields=["status", "closed_at"])
            stale_count += 1

    logger.info(
        "auto_close_stale_jobs: %d deadline-expired, %d stale jobs closed",
        deadline_count,
        stale_count,
    )
    return {"deadline_closed": deadline_count, "stale_closed": stale_count}


# ---------------------------------------------------------------------------
# #59 — Interview reminder emails (24h and 1h before interview)
# ---------------------------------------------------------------------------

@shared_task(name="apps.jobs.tasks.send_interview_reminders")
def send_interview_reminders():
    """
    Runs every 30 minutes.  Sends reminder emails to candidates and
    interviewers for upcoming interviews.

    Windows:
      - 24-hour reminder: interviews starting between now+23h and now+25h
      - 1-hour reminder:  interviews starting between now+50min and now+70min
    """
    from django.core.mail import send_mail
    from django.conf import settings

    # Attempt to import Interview model — may be in applications or interviews app
    try:
        from apps.applications.models import Interview
    except ImportError:
        try:
            from apps.interviews.models import Interview
        except ImportError:
            logger.warning("send_interview_reminders: Interview model not found, skipping")
            return {"sent": 0}

    now = timezone.now()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@connectos.io")
    sent_count = 0

    windows = [
        (timezone.timedelta(hours=23), timezone.timedelta(hours=25), "24h"),
        (timezone.timedelta(minutes=50), timezone.timedelta(minutes=70), "1h"),
    ]

    for delta_low, delta_high, reminder_label in windows:
        start_from = now + delta_low
        start_to = now + delta_high

        interviews_qs = Interview.objects.filter(
            date__gte=start_from.date(),
            date__lte=start_to.date(),
            status__in=["scheduled", "confirmed"],
        ).select_related("application__candidate", "application__job", "interviewer")

        for interview in interviews_qs:
            candidate = getattr(interview, "candidate", None)
            job = getattr(interview, "job", None)
            if not candidate or not job:
                continue

            candidate_email = getattr(candidate, "primary_email", None)
            interviewer_email = getattr(getattr(interview, "interviewer", None), "email", None)

            interview_time = str(interview.date)
            body = (
                f"Reminder ({reminder_label}): Interview for {job.title}\n"
                f"Scheduled: {interview_time}\n\n"
                f"Please confirm attendance or contact us if you need to reschedule."
            )

            for email in filter(None, [candidate_email, interviewer_email]):
                try:
                    send_mail(
                        subject=f"[{reminder_label} Reminder] Interview — {job.title}",
                        message=body,
                        from_email=from_email,
                        recipient_list=[email],
                        fail_silently=True,
                    )
                    sent_count += 1
                except Exception as exc:
                    logger.warning("reminder email failed to %s: %s", email, exc)

    logger.info("send_interview_reminders: %d emails sent", sent_count)
    return {"sent": sent_count}


# ---------------------------------------------------------------------------
# #61 — Candidate data retention enforcement (GDPR right to erasure)
# ---------------------------------------------------------------------------

@shared_task(name="apps.jobs.tasks.enforce_candidate_retention")
def enforce_candidate_retention():
    """
    Weekly task: anonymise or delete candidate profiles whose
    `data_retention_until` date has passed.

    Strategy:
      - Anonymise: replace PII fields with placeholders, mark as anonymised.
      - Hard delete only if tenant policy requires it.
    """
    from apps.candidates.models import Candidate
    from apps.tenants.models import TenantSettings

    now = timezone.now()
    anonymised = 0
    deleted = 0

    expired_qs = Candidate.objects.filter(
        data_retention_until__lte=now,
    ).exclude(
        primary_email__startswith="anon_",  # already processed
    ).select_related("tenant")

    for candidate in expired_qs:
        settings_obj = TenantSettings.objects.filter(tenant=candidate.tenant).first()
        hard_delete = getattr(settings_obj, "gdpr_hard_delete", False)

        try:
            if hard_delete:
                candidate.delete()
                deleted += 1
            else:
                # Anonymise PII in place
                candidate.primary_email = f"anon_{candidate.id}@deleted.invalid"
                candidate.full_name = "Anonymised User"
                candidate.primary_phone = ""
                candidate.location = ""
                candidate.headline = ""
                candidate.linkedin_url = ""
                candidate.portfolio_url = ""
                candidate.tags = []
                candidate.source_metadata = {}
                candidate.data_retention_until = None
                candidate.save(update_fields=[
                    "primary_email", "full_name",
                    "primary_phone", "location", "headline",
                    "linkedin_url", "portfolio_url", "tags",
                    "source_metadata", "data_retention_until",
                ])
                anonymised += 1
        except Exception as exc:
            logger.error("retention: failed for candidate %s: %s", candidate.id, exc)

    logger.info(
        "enforce_candidate_retention: %d anonymised, %d deleted", anonymised, deleted
    )
    return {"anonymised": anonymised, "deleted": deleted}
