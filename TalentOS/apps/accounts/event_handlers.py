"""TalentOS — ConnectOS platform event handlers.

Registered via settings.py::

    PLATFORM_EVENT_HANDLERS = {
        "application.submitted":  "apps.accounts.event_handlers.on_application_submitted",
        "job.posted":             "apps.accounts.event_handlers.on_job_posted_broadcast",
        "employee.offboarded":    "apps.accounts.event_handlers.on_employee_offboarded",
    }
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def on_application_submitted(payload: dict[str, Any]) -> None:
    """
    A candidate submitted an application (originated in CareerOS / Job Finder).
    Import it into the TalentOS ATS pipeline so recruiters see it immediately.

    Payload keys:
        person_id       – cx_person UUID
        job_post_id     – cx_job_post UUID
        tenant_id       – cx_tenant UUID
        application_id  – portal-local application UUID (from the originating portal)
        source_portal   – which portal the application came from
        resume_url      – optional S3/CDN URL
    """
    from apps.applications.models import Application
    from apps.candidates.models import Candidate
    from apps.jobs.models import Job

    person_id    = payload.get("person_id")
    job_post_id  = payload.get("job_post_id")
    tenant_id    = payload.get("tenant_id")
    source_portal = payload.get("source_portal", "external")

    if not person_id or not job_post_id:
        logger.warning(
            "on_application_submitted: missing person_id or job_post_id — payload=%s",
            payload,
        )
        return

    # Find the local Job row that mirrors this canonical job post
    try:
        job = Job.objects.get(platform_job_post_id=job_post_id)
    except Job.DoesNotExist:
        logger.warning(
            "on_application_submitted: no local Job mirrors platform_job_post_id=%s",
            job_post_id,
        )
        return

    # Upsert candidate record
    candidate, _ = Candidate.objects.get_or_create(
        platform_person_id=person_id,
        defaults={"resume_url": payload.get("resume_url", "")},
    )

    # Create application only if not already imported
    app, created = Application.objects.get_or_create(
        candidate=candidate,
        job=job,
        defaults={
            "source": source_portal,
            "stage": "applied",
            "platform_application_id": payload.get("application_id"),
        },
    )

    logger.info(
        "on_application_submitted: application %s for candidate %s on job %s",
        "created" if created else "already exists",
        person_id,
        job_post_id,
    )


def on_job_posted_broadcast(payload: dict[str, Any]) -> None:
    """
    A canonical JobPost was published. Ensure a matching local Job row exists
    so TalentOS recruiters see all live roles regardless of which sub-tenant
    originally posted the job.

    Payload keys (matches platform_jobs.JobPost fields):
        job_post_id     – cx_job_post UUID
        title           – job title
        tenant_id       – cx_tenant UUID
        visible_on_portals – list of portal codenames
    """
    from apps.jobs.models import Job

    job_post_id = payload.get("job_post_id")
    if not job_post_id:
        return

    # Only sync if TalentOS is listed as a target portal
    visible = payload.get("visible_on_portals", [])
    if "talentos" not in visible and visible:
        return

    Job.objects.get_or_create(
        platform_job_post_id=job_post_id,
        defaults={
            "title": payload.get("title", ""),
            "tenant_id": payload.get("tenant_id"),
            "status": "published",
        },
    )
    logger.info("on_job_posted_broadcast: synced job_post_id=%s", job_post_id)


def on_employee_offboarded(payload: dict[str, Any]) -> None:
    """
    An employee has been offboarded from WorkforceOS.
    Re-open the requisition if the position should be backfilled.

    Payload keys:
        person_id  – cx_person UUID
        tenant_id  – cx_tenant UUID
        reason     – "resignation" | "termination" | "retirement" | "contract_end"
    """
    logger.info(
        "on_employee_offboarded: received in TalentOS for person_id=%s reason=%s",
        payload.get("person_id"),
        payload.get("reason"),
    )
    # Backfill logic: portal teams implement per-client rules here
