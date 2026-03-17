"""Celery tasks for Job Architecture app."""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.job_architecture.tasks.flag_expiring_salary_bands")
def flag_expiring_salary_bands():
    """
    Weekly: flag salary bands expiring within 30 days so compensation
    ops can refresh them before they lapse.
    """
    from apps.job_architecture.models import SalaryBand

    now = timezone.now().date()
    threshold = now + timezone.timedelta(days=30)
    expiring = SalaryBand.objects.filter(expiry_date__lte=threshold, expiry_date__gte=now)
    count = expiring.count()
    logger.info("flag_expiring_salary_bands: %d bands expiring within 30 days", count)
    return {"expiring_bands": count}


@shared_task(name="apps.job_architecture.tasks.sync_headcount_requisition_status")
def sync_headcount_requisition_status():
    """
    Daily: mark HeadcountRequisitions as 'filled' when their linked job
    has been hired and headcount target is met.
    """
    from apps.job_architecture.models import HeadcountRequisition

    filled = 0
    qs = HeadcountRequisition.objects.filter(status="in_progress").select_related("linked_job")
    for req in qs:
        job = req.linked_job
        if job and job.headcount_filled >= job.headcount_target:
            req.status = "filled"
            req.save(update_fields=["status"])
            filled += 1
    logger.info("sync_headcount_requisition_status: %d requisitions marked filled", filled)
    return {"filled": filled}
