"""
ATS → HRM cross-system drift reconciliation task.

This task runs periodically to detect records that should have been synced
from ATS to HRM (or vice versa) but were missed due to:
  - temporary network failures during webhook delivery
  - service downtime
  - manual data corrections

Reconciliation strategy:
  1. Fetch all ATS Offers with status=ACCEPTED and no hrm_employee_id set
     AND older than 10 minutes (giving the real-time webhook a chance first).
  2. Re-fire the offer.accepted webhook payload to the HRM bridge endpoint.
  3. Log any failures for operator review.
"""

import hashlib
import hmac
import json
import logging
import urllib.request
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('ats.tasks')


@shared_task(bind=True, max_retries=3, default_retry_delay=300, name='ats.sync_ats_hrm_drift')
def sync_ats_hrm_drift(self):
    """
    Detect offer records that were accepted in ATS but never synced to HRM,
    and re-fire the bridge webhook for each one.

    Scheduled: every 30 minutes via CELERY_BEAT_SCHEDULE.
    """
    try:
        from apps.jobs.models import Offer  # noqa: import inside task to avoid circular
    except ImportError:
        logger.warning('sync_ats_hrm_drift: Offer model not found — skipping')
        return {'synced': 0, 'errors': []}

    hrm_bridge_url = getattr(settings, 'HRM_BRIDGE_URL', None)
    if not hrm_bridge_url:
        logger.info('sync_ats_hrm_drift: HRM_BRIDGE_URL not configured — skipping drift check')
        return {'synced': 0, 'errors': []}

    secret = getattr(settings, 'ATS_WEBHOOK_SECRET', '') or getattr(settings, 'SHARED_JWT_SECRET', '')

    # Find offers accepted more than 10 minutes ago but still missing hrm_employee_id
    cutoff = timezone.now() - timedelta(minutes=10)
    unsynced_offers = Offer.objects.filter(
        status='accepted',
        hrm_employee_id__isnull=True,
        accepted_at__lte=cutoff,
    ).select_related('candidate', 'job_posting', 'job_posting__department').order_by('accepted_at')[:50]

    synced = 0
    errors = []

    for offer in unsynced_offers:
        try:
            payload = _build_offer_payload(offer)
            body = json.dumps(payload).encode('utf-8')

            headers = {
                'Content-Type': 'application/json',
                'X-ATS-Event': 'offer.accepted',
                'X-ATS-Drift-Sync': '1',  # marker so HRM can log it differently
            }

            if secret:
                sig = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
                headers['X-ATS-Signature'] = sig

            req = urllib.request.Request(
                hrm_bridge_url,
                data=body,
                headers=headers,
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    synced += 1
                    logger.info('drift_sync: re-fired offer %s → HRM (HTTP %s)', offer.id, resp.status)
                else:
                    errors.append({'offer_id': str(offer.id), 'error': f'HTTP {resp.status}'})
                    logger.warning('drift_sync: offer %s → HRM returned HTTP %s', offer.id, resp.status)

        except Exception as exc:
            errors.append({'offer_id': str(offer.id), 'error': str(exc)})
            logger.error('drift_sync: failed to re-fire offer %s: %s', offer.id, exc, exc_info=True)

    logger.info('sync_ats_hrm_drift complete: %d synced, %d errors', synced, len(errors))
    return {'synced': synced, 'errors': errors}


def _build_offer_payload(offer) -> dict:
    """Build the same payload structure as the real-time offer.accepted webhook."""
    candidate = offer.candidate
    job = getattr(offer, 'job_posting', None)
    dept = getattr(job, 'department', None) if job else None

    return {
        'event': 'offer.accepted',
        'offer_id': str(offer.id),
        'candidate': {
            'id': str(candidate.id),
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'email': candidate.email,
            'phone': getattr(candidate, 'phone', ''),
        },
        'offer': {
            'id': str(offer.id),
            'salary': str(offer.salary_offered) if getattr(offer, 'salary_offered', None) else None,
            'currency': getattr(offer, 'currency', 'LKR'),
            'start_date': offer.start_date.isoformat() if getattr(offer, 'start_date', None) else None,
            'employment_type': getattr(offer, 'employment_type', 'full_time'),
        },
        'job': {
            'id': str(job.id) if job else None,
            'title': job.title if job else None,
            'department': dept.name if dept else None,
            'department_id': str(dept.id) if dept else None,
        },
        'metadata': {
            'drift_sync': True,
            'ats_tenant_id': str(getattr(offer, 'tenant_id', '')),
        },
    }
