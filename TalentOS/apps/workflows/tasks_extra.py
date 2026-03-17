"""Additional Celery tasks for scheduled messages, bounces, stale detection, and weekly reports."""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name="apps.workflows.tasks.detect_stale_candidates")
def detect_stale_candidates():
    """Find candidates inactive for 30+ days and tag them as stale."""
    from apps.candidates.models import Candidate

    threshold = timezone.now() - timedelta(days=30)
    stale = Candidate.objects.filter(
        updated_at__lt=threshold,
    ).exclude(tags__contains=["stale"])

    count = 0
    for candidate in stale[:500]:
        tags = candidate.tags or []
        if "stale" not in tags:
            tags.append("stale")
            candidate.tags = tags
            candidate.save(update_fields=["tags", "updated_at"])
            count += 1

    logger.info(f"detect_stale_candidates: tagged {count} stale candidates")
    return {"tagged": count}


@shared_task(name="apps.workflows.tasks.check_offer_expirations")
def check_offer_expirations():
    """Mark expired offers and notify recruiters."""
    from apps.applications.models import Offer

    today = timezone.now().date()
    expired = Offer.objects.filter(
        status="pending",
        expires_at__lt=today,
    )
    count = expired.update(status="expired")
    logger.info(f"check_offer_expirations: expired {count} offers")
    return {"expired": count}
