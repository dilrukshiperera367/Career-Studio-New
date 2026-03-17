"""WorkforceOS — ConnectOS platform event handlers.

These functions are called by `platform_events.consumer.consume_streams`
whenever the Celery worker receives a cross-portal event that WorkforceOS
cares about.

Register all handlers in settings.py::

    PLATFORM_EVENT_HANDLERS = {
        "application.offer_accepted": "authentication.event_handlers.on_offer_accepted",
        "employee.offboarded":        "authentication.event_handlers.on_employee_offboarded",
        "person.created":             "authentication.event_handlers.on_person_created",
    }
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def on_offer_accepted(payload: dict[str, Any]) -> None:
    """
    A job offer has been accepted in TalentOS.
    Create or activate the corresponding Employee record in WorkforceOS.

    Payload keys (as published by TalentOS):
        person_id      – cx_person UUID
        job_post_id    – cx_job_post UUID
        tenant_id      – cx_tenant UUID
        start_date     – ISO-8601 date string (optional)
        offer_id       – portal-local offer UUID
    """
    from core_hr.models import Employee  # local import to avoid circular deps

    person_id  = payload.get("person_id")
    tenant_id  = payload.get("tenant_id")
    job_post_id = payload.get("job_post_id")
    start_date  = payload.get("start_date")

    if not person_id or not tenant_id:
        logger.warning(
            "on_offer_accepted: missing person_id or tenant_id in payload %s",
            payload,
        )
        return

    employee, created = Employee.objects.get_or_create(
        platform_person_id=person_id,
        tenant_id=tenant_id,
        defaults={
            "status": "pending_onboarding",
            "platform_job_post_id": job_post_id,
            "expected_start_date": start_date,
        },
    )

    if not created and employee.status == "inactive":
        # Re-hire scenario
        employee.status = "pending_onboarding"
        employee.expected_start_date = start_date
        employee.save(update_fields=["status", "expected_start_date"])

    logger.info(
        "on_offer_accepted: employee %s for person %s (%s)",
        "created" if created else "reactivated",
        person_id,
        employee.pk,
    )


def on_employee_offboarded(payload: dict[str, Any]) -> None:
    """
    Fired by WorkforceOS itself (or TalentOS) when an employee's offboarding
    is complete. Marks the Employee record inactive and notifies CareerOS to
    activate an alumni profile via a return publish.

    Payload keys:
        person_id   – cx_person UUID
        tenant_id   – cx_tenant UUID
        last_day    – ISO-8601 date string
        reason      – "resignation" | "termination" | "retirement" | "contract_end"
    """
    from core_hr.models import Employee
    from platform_events.producer import publish
    from platform_events.events import EMPLOYEE_OFFBOARDED

    person_id = payload.get("person_id")
    tenant_id = payload.get("tenant_id")

    if not person_id:
        logger.warning("on_employee_offboarded: missing person_id in payload %s", payload)
        return

    updated = Employee.objects.filter(
        platform_person_id=person_id,
        tenant_id=tenant_id,
        status__in=["active", "on_leave"],
    ).update(status="inactive")

    logger.info(
        "on_employee_offboarded: marked %d employee record(s) inactive for person %s",
        updated,
        person_id,
    )

    # Re-publish so CareerOS can activate the alumni profile
    publish(
        event_type=EMPLOYEE_OFFBOARDED,
        payload=payload,
        source_portal="workforceos",
    )


def on_person_created(payload: dict[str, Any]) -> None:
    """
    A new canonical Person was created in ConnectOS.
    Pre-warm a WorkforceOS employee shell record to speed up future onboarding.
    This is a no-op if the employee row already exists.

    Payload keys:
        person_id  – cx_person UUID
        email      – email address
    """
    logger.debug(
        "on_person_created: received for person_id=%s — no action needed in WorkforceOS",
        payload.get("person_id"),
    )
