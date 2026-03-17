"""Platform Core services — timeline events, notifications, webhooks."""

import logging
from django.utils import timezone
from .models import TimelineEvent, Notification

logger = logging.getLogger('hrm')


def emit_timeline_event(tenant_id, employee, event_type, category, title,
                        actor=None, actor_type='user', description='',
                        source_object_type='', source_object_id=None, metadata=None):
    """Create a timeline event for an employee."""
    try:
        return TimelineEvent.objects.create(
            tenant_id=tenant_id,
            employee=employee,
            event_type=event_type,
            category=category,
            title=title,
            description=description,
            actor=actor,
            actor_type=actor_type,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.error(f"Failed to emit timeline event: {e}")
        return None


def send_notification(tenant_id, recipient, title, body='', type='info',
                      channel='in_app', action_url='', metadata=None):
    """Create a notification for a user."""
    try:
        return Notification.objects.create(
            tenant_id=tenant_id,
            recipient=recipient,
            title=title,
            body=body,
            type=type,
            channel=channel,
            action_url=action_url,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return None


def send_email_notification(recipient_email, subject, body_html, tenant_id=None):
    """Send email notification (async via Celery in production)."""
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        send_mail(
            subject=subject,
            message='',
            html_message=body_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
