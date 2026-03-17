"""
Webhook dispatch service — sends HMAC-signed webhook events to subscribers.
"""

import hashlib
import hmac
import json
import uuid
import logging
from datetime import datetime

import requests
from django.conf import settings

from .models import WebhookSubscription, WebhookDelivery

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
TIMEOUT_SECONDS = 10


def dispatch_webhook_event(tenant, event_type, payload):
    """
    Dispatch a webhook event to all subscribers listening for this event type.

    Args:
        tenant: Tenant instance
        event_type: e.g. 'employee.created', 'leave.approved', 'payroll.finalized'
        payload: dict of event data
    """
    subscriptions = WebhookSubscription.objects.filter(
        tenant=tenant,
        is_active=True,
    ).filter(
        events__contains=[event_type]
    )

    results = []
    for sub in subscriptions:
        delivery = _deliver_webhook(sub, event_type, payload)
        results.append(delivery)

    return results


def _deliver_webhook(subscription, event_type, payload, attempt=1):
    """Deliver a single webhook with HMAC signature."""
    delivery_id = str(uuid.uuid4())

    body = json.dumps({
        'id': delivery_id,
        'event': event_type,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'data': payload,
    }, default=str)

    # HMAC-SHA256 signature
    signature = hmac.new(
        subscription.secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-Signature': f'sha256={signature}',
        'X-Webhook-Event': event_type,
        'X-Webhook-Delivery': delivery_id,
        'User-Agent': 'ConnectHR-Webhook/1.0',
    }

    try:
        response = requests.post(
            subscription.target_url,
            data=body,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )

        delivery = WebhookDelivery.objects.create(
            subscription=subscription,
            event_type=event_type,
            payload=json.loads(body),
            response_status=response.status_code,
            response_body=response.text[:2000],
            success=200 <= response.status_code < 300,
            attempt=attempt,
        )

        if not delivery.success and attempt < MAX_RETRIES:
            logger.warning(f"Webhook delivery failed (attempt {attempt}), retrying...")
            return _deliver_webhook(subscription, event_type, payload, attempt + 1)

        return delivery

    except requests.RequestException as e:
        delivery = WebhookDelivery.objects.create(
            subscription=subscription,
            event_type=event_type,
            payload=json.loads(body),
            response_status=0,
            success=False,
            attempt=attempt,
            error=str(e),
        )

        if attempt < MAX_RETRIES:
            return _deliver_webhook(subscription, event_type, payload, attempt + 1)

        return delivery
