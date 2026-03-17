"""Job Finder — ConnectOS platform event handlers.

Registered via settings.py::

    PLATFORM_EVENT_HANDLERS = {
        "job.posted":   "apps.jobs.event_handlers.on_job_posted",
        "job.updated":  "apps.jobs.event_handlers.on_job_updated",
        "job.closed":   "apps.jobs.event_handlers.on_job_closed",
    }
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def on_job_posted(payload: dict[str, Any]) -> None:
    """
    Sync a canonical cx_job_post into the Job Finder local jobs table.

    Payload keys:
        job_post_id        – cx_job_post UUID
        title              – job title
        tenant_id          – cx_tenant UUID
        description_html   – optional rich HTML
        pay_min / pay_max  – decimal salary bounds
        country            – ISO-3166 alpha-2 (for job quality / foreign posting checks)
        eligible_countries – list of ISO codes
        visible_on_portals – list of portal codenames
    """
    from apps.jobs.models import Job

    job_post_id = payload.get("job_post_id")
    visible     = payload.get("visible_on_portals", [])

    if not job_post_id:
        return

    if visible and "jobfinder" not in visible:
        return

    Job.objects.update_or_create(
        platform_job_post_id=job_post_id,
        defaults={
            "title":             payload.get("title", ""),
            "tenant_id":         payload.get("tenant_id"),
            "description_html":  payload.get("description_html", ""),
            "pay_min":           payload.get("pay_min"),
            "pay_max":           payload.get("pay_max"),
            "country":           payload.get("country", ""),
            "eligible_countries": payload.get("eligible_countries", []),
            "status":            "active",
        },
    )
    logger.info("on_job_posted: synced job_post_id=%s to Job Finder", job_post_id)


def on_job_updated(payload: dict[str, Any]) -> None:
    on_job_posted(payload)


def on_job_closed(payload: dict[str, Any]) -> None:
    from apps.jobs.models import Job

    job_post_id = payload.get("job_post_id")
    if not job_post_id:
        return

    Job.objects.filter(platform_job_post_id=job_post_id).update(status="closed")
    logger.info("on_job_closed: closed job_post_id=%s in Job Finder", job_post_id)
