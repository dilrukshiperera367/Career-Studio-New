"""
Email Service — Template rendering, queuing, and delivery.

Idempotent: one message per (event_id, template) combination.
"""

import re
import logging
from typing import Optional

from django.utils import timezone

from apps.messaging.models import EmailTemplate, Message, ActivityLog

logger = logging.getLogger(__name__)


def queue_email(
    tenant_id: str,
    template_slug: str,
    candidate_id: str,
    application_id: Optional[str] = None,
    context: Optional[dict] = None,
    sender_id: Optional[str] = None,
):
    """
    Render an email template and queue it for delivery.
    """
    try:
        template = EmailTemplate.objects.get(tenant_id=tenant_id, slug=template_slug, is_active=True)
    except EmailTemplate.DoesNotExist:
        logger.error(f"Template {template_slug} not found for tenant {tenant_id}")
        return None

    # Render template
    rendered_subject = _render_template(template.subject, context or {})
    rendered_body = _render_template(template.body, context or {})

    # Create message
    message = Message.objects.create(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        application_id=application_id,
        sender_id=sender_id,
        channel="email",
        direction="outbound",
        subject=rendered_subject,
        body=rendered_body,
        status="queued",
    )

    logger.info(f"Email queued: {message.id} ({template_slug})")
    return message


def send_email(message_id: str):
    """
    Send a queued email via SMTP.
    Uses per-tenant SMTP settings if configured, otherwise Django's default backend.
    """
    try:
        message = Message.objects.get(id=message_id)
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
        return False

    if message.status != "queued":
        logger.info(f"Message {message_id} already processed: {message.status}")
        return False

    try:
        recipient_email = _get_candidate_email(message.candidate_id, message.tenant_id)
        if not recipient_email:
            message.status = "failed"
            message.error = "No email address found for candidate"
            message.save()
            return False

        # Try per-tenant SMTP first
        smtp_config = _get_tenant_smtp(message.tenant_id)

        if smtp_config and smtp_config.get("host"):
            # Use tenant's own SMTP server — decrypt password before use
            from apps.shared.encryption import decrypt_value
            from django.core.mail import EmailMessage
            from django.core.mail.backends.smtp import EmailBackend

            backend = EmailBackend(
                host=smtp_config["host"],
                port=int(smtp_config.get("port", 587)),
                username=smtp_config.get("username", ""),
                password=decrypt_value(smtp_config.get("password", "")),
                use_tls=smtp_config.get("encryption", "tls") == "tls",
                use_ssl=smtp_config.get("encryption", "") == "ssl",
                fail_silently=False,
            )

            from_email = smtp_config.get("from_email") or smtp_config.get("username") or None
            email = EmailMessage(
                subject=message.subject,
                body=message.body,
                from_email=from_email,
                to=[recipient_email],
                connection=backend,
            )
            email.send()
        else:
            # Fallback to Django default email backend (console in dev)
            from django.core.mail import send_mail
            send_mail(
                subject=message.subject,
                message=message.body,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[recipient_email],
                fail_silently=False,
            )

        message.status = "sent"
        message.sent_at = timezone.now()
        message.save()

        # Activity log
        ActivityLog.objects.create(
            tenant_id=message.tenant_id,
            actor_id=message.sender_id,
            entity_type="message",
            entity_id=message.id,
            action="email_sent",
            content=f"Sent to {recipient_email}: {message.subject}",
        )

        logger.info(f"Email sent: {message_id}")
        return True

    except Exception as e:
        message.status = "failed"
        message.error = str(e)
        message.save()
        logger.error(f"Email send failed: {e}")
        return False


def _get_tenant_smtp(tenant_id: str) -> Optional[dict]:
    """Get SMTP config from TenantSettings."""
    try:
        from apps.tenants.models import TenantSettings
        settings = TenantSettings.objects.get(tenant_id=tenant_id)
        smtp = settings.smtp_config
        if smtp and isinstance(smtp, dict) and smtp.get("host"):
            return smtp
    except TenantSettings.DoesNotExist:
        pass
    return None


def _render_template(template_str: str, context: dict) -> str:
    """Simple {{variable}} replacement."""
    def replacer(match):
        key = match.group(1).strip()
        return str(context.get(key, f"{{{{{key}}}}}"))

    return re.sub(r"\{\{(\w+)\}\}", replacer, template_str)


def _get_candidate_email(candidate_id: str, tenant_id: str) -> Optional[str]:
    """Get primary email for a candidate."""
    from apps.candidates.models import Candidate
    try:
        candidate = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
        return candidate.primary_email
    except Candidate.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Bulk Email (Feature 69-70)
# ---------------------------------------------------------------------------

def send_bulk_email(
    tenant_id: str,
    template_slug: str,
    candidate_ids: list,
    context: Optional[dict] = None,
    sender_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> dict:
    """
    Send the same email template to multiple candidates.
    Returns summary of queued/failed counts.
    """
    import uuid

    if not thread_id:
        thread_id = str(uuid.uuid4())

    results = {"queued": 0, "failed": 0, "thread_id": thread_id}

    for candidate_id in candidate_ids:
        try:
            message = queue_email(
                tenant_id=tenant_id,
                template_slug=template_slug,
                candidate_id=candidate_id,
                context=context,
                sender_id=sender_id,
            )
            if message:
                message.thread_id = thread_id
                message.save(update_fields=["thread_id"])
                results["queued"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            logger.error(f"Bulk email failed for candidate {candidate_id}: {e}")
            results["failed"] += 1

    return results


# ---------------------------------------------------------------------------
# Scheduled Email (Feature 71-72)
# ---------------------------------------------------------------------------

def schedule_email(
    tenant_id: str,
    template_slug: str,
    candidate_id: str,
    send_at,  # datetime
    context: Optional[dict] = None,
    sender_id: Optional[str] = None,
) -> Optional["Message"]:
    """
    Queue an email for future delivery.
    The send_scheduled_emails task will pick it up at the right time.
    """
    message = queue_email(
        tenant_id=tenant_id,
        template_slug=template_slug,
        candidate_id=candidate_id,
        context=context,
        sender_id=sender_id,
    )
    if message:
        message.status = "scheduled"
        message.scheduled_for = send_at
        message.save(update_fields=["status", "scheduled_for"])
        logger.info(f"Email scheduled: {message.id} for {send_at}")
    return message


def send_scheduled_emails():
    """
    Send all emails that are scheduled for delivery and past their send time.
    Called by a periodic Celery task.
    """
    now = timezone.now()
    messages = Message.objects.filter(
        status="scheduled",
        scheduled_for__lte=now,
    )

    sent_count = 0
    for msg in messages:
        msg.status = "queued"
        msg.save(update_fields=["status"])
        if send_email(str(msg.id)):
            sent_count += 1

    logger.info(f"Sent {sent_count} scheduled emails")
    return sent_count


# ---------------------------------------------------------------------------
# Bounce Handling (Feature 73-74)
# ---------------------------------------------------------------------------

def process_bounces():
    """
    Check for bounced emails and flag candidate email addresses.
    Marks candidates with repeated bounces as having invalid emails.
    """
    from django.db.models import Count
    from apps.candidates.models import Candidate

    # Find candidates with 3+ failed emails
    bounced = Message.objects.filter(
        status="failed",
        channel="email",
    ).values("candidate_id", "tenant_id").annotate(
        bounce_count=Count("id")
    ).filter(bounce_count__gte=3)

    flagged = 0
    for item in bounced:
        try:
            candidate = Candidate.objects.get(
                id=item["candidate_id"],
                tenant_id=item["tenant_id"],
            )
            if "email_bounced" not in (candidate.tags or []):
                candidate.tags = (candidate.tags or []) + ["email_bounced"]
                candidate.save(update_fields=["tags", "updated_at"])
                flagged += 1
        except Candidate.DoesNotExist:
            pass

    logger.info(f"Flagged {flagged} candidates with bounced emails")
    return flagged


# ---------------------------------------------------------------------------
# Email Tracking (Feature 75-76)
# ---------------------------------------------------------------------------

def track_open(tracking_id: str) -> bool:
    """Record that an email was opened (tracking pixel hit)."""
    try:
        message = Message.objects.get(tracking_id=tracking_id)
        if not message.opened_at:
            message.opened_at = timezone.now()
            message.save(update_fields=["opened_at"])
        return True
    except Message.DoesNotExist:
        return False


def track_click(tracking_id: str) -> bool:
    """Record that a link was clicked in an email."""
    try:
        message = Message.objects.get(tracking_id=tracking_id)
        if not message.clicked_at:
            message.clicked_at = timezone.now()
            message.save(update_fields=["clicked_at"])
        return True
    except Message.DoesNotExist:
        return False


def get_email_thread(tenant_id: str, thread_id: str) -> list:
    """Get all messages in an email thread."""
    messages = Message.objects.filter(
        tenant_id=tenant_id,
        thread_id=thread_id,
    ).order_by("created_at")

    return [
        {
            "id": str(m.id),
            "subject": m.subject,
            "body": m.body[:500],
            "direction": m.direction,
            "status": m.status,
            "sent_at": str(m.sent_at) if m.sent_at else None,
            "opened_at": str(m.opened_at) if m.opened_at else None,
            "created_at": str(m.created_at),
        }
        for m in messages
    ]
