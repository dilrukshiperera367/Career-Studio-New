"""Celery tasks for Compensation Ops."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.compensation_ops.tasks.flag_expiring_compensation_bands")
def flag_expiring_compensation_bands():
    """
    Daily task: flag CompensationBands expiring within the next 30 days
    by creating CompetitivenessAlerts.
    """
    from apps.compensation_ops.models import CompensationBand, CompetitivenessAlert

    cutoff = (timezone.now() + timezone.timedelta(days=30)).date()
    today = timezone.now().date()

    expiring = CompensationBand.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=cutoff,
    )

    created = 0
    for band in expiring:
        _, was_created = CompetitivenessAlert.objects.get_or_create(
            tenant=band.tenant,
            alert_type="band_expiring",
            job_family_ref=band.job_family_ref,
            level_ref=band.level_ref,
            geo_zone=band.geo_zone,
            is_resolved=False,
            defaults={
                "severity": "warning",
                "message": (
                    f"Compensation band '{band.name}' ({band.geo_zone or 'Global'}) "
                    f"expires on {band.expiry_date}."
                ),
            },
        )
        if was_created:
            created += 1

    logger.info("flag_expiring_compensation_bands: %d alerts created", created)
    return {"alerts_created": created}


@shared_task(name="apps.compensation_ops.tasks.expire_pending_offer_approvals")
def expire_pending_offer_approvals():
    """
    Daily task: mark OfferApprovalSteps that have been pending for more than
    72 hours as needing escalation (log a warning).
    """
    from apps.compensation_ops.models import OfferApprovalStep

    threshold = timezone.now() - timezone.timedelta(hours=72)
    stale = OfferApprovalStep.objects.filter(
        status="pending",
        created_at__lte=threshold,
    ).select_related("offer", "approver")

    count = 0
    for step in stale:
        logger.warning(
            "Stale offer approval: offer=%s step=%s approver=%s pending since %s",
            step.offer_id,
            step.step_order,
            step.approver_id,
            step.created_at,
        )
        count += 1

    logger.info("expire_pending_offer_approvals: %d stale steps logged", count)
    return {"stale_steps": count}
