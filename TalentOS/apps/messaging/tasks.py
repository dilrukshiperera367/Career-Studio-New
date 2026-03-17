"""Celery tasks for messaging."""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, message_id: str):
    """Send a queued email."""
    try:
        from apps.messaging.services import send_email
        send_email(message_id)
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise self.retry(exc=e)
