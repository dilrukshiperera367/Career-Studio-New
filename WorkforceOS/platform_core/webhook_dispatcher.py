"""
Outbound webhook dispatcher for HRM.
Sends event notifications to tenant-configured webhook endpoints.
"""
import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import timedelta
import requests
from django.conf import settings
from django.utils import timezone
from celery import shared_task

logger = logging.getLogger('connecthr.webhooks')


# ─── Webhook Event Types ──────────────────────────────────────────────────────

class WebhookEvent:
    # Employee events
    EMPLOYEE_CREATED = 'employee.created'
    EMPLOYEE_UPDATED = 'employee.updated'
    EMPLOYEE_TERMINATED = 'employee.terminated'
    # Leave events
    LEAVE_REQUESTED = 'leave.requested'
    LEAVE_APPROVED = 'leave.approved'
    LEAVE_REJECTED = 'leave.rejected'
    # Payroll events
    PAYROLL_RUN_COMPLETED = 'payroll.run_completed'
    PAYSLIP_GENERATED = 'payslip.generated'
    # Performance events
    REVIEW_SUBMITTED = 'review.submitted'
    GOAL_COMPLETED = 'goal.completed'


# ─── Dispatcher ──────────────────────────────────────────────────────────────

def dispatch_webhook(tenant_id: str, event_type: str, payload: dict):
    """
    Dispatch a webhook event asynchronously via Celery.
    Call this from signal handlers or view post-save logic.
    """
    deliver_webhook_event.delay(
        tenant_id=str(tenant_id),
        event_type=event_type,
        payload=payload,
        event_id=str(uuid.uuid4()),
        timestamp=timezone.now().isoformat(),
    )


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def deliver_webhook_event(self, tenant_id: str, event_type: str, payload: dict,
                           event_id: str, timestamp: str):
    """Celery task: deliver a webhook event to all tenant endpoint subscriptions."""
    try:
        from platform_core.models import WebhookSubscription
        subscriptions = WebhookSubscription.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            events__contains=event_type,
        )
    except Exception:
        # If WebhookSubscription model doesn't exist yet, gracefully exit
        logger.debug('WebhookSubscription model not available yet, skipping delivery.')
        return

    envelope = {
        'id': event_id,
        'type': event_type,
        'created': timestamp,
        'data': payload,
    }
    body = json.dumps(envelope, default=str)

    for sub in subscriptions:
        try:
            _deliver_to_endpoint(sub, body, event_id)
        except Exception as exc:
            logger.warning('Webhook delivery failed to %s: %s', sub.url, exc)
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                logger.error('Max retries exceeded for webhook %s', sub.id)


def _deliver_to_endpoint(sub, body: str, event_id: str):
    """Sign and POST the webhook payload to a single endpoint."""
    secret = getattr(sub, 'secret', '') or ''
    signature = ''
    if secret:
        signature = hmac.new(
            secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256
        ).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-ConnectOS-Event-ID': event_id,
        'X-ConnectOS-Signature': f'sha256={signature}',
        'User-Agent': 'ConnectOS-Webhook/1.0',
    }

    resp = requests.post(sub.url, data=body, headers=headers, timeout=10)
    resp.raise_for_status()
    logger.info('Webhook delivered to %s: HTTP %d', sub.url, resp.status_code)
