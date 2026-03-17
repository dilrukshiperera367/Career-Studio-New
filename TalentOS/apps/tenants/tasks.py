"""Celery tasks for tenant/trial lifecycle management."""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='tenants.check_trial_expirations')
def check_trial_expirations(self):
    """Mark expired trials and send 3-day warning emails."""
    from .models import Tenant
    from apps.accounts.models import Subscription  # noqa: F401 – available for downstream use

    now = timezone.now()

    # Mark newly expired trials
    expired_count = Tenant.objects.filter(
        status='trial',
        trial_ends_at__lte=now,
    ).update(status='expired')

    # 3-day warning emails
    warning_date = now + timezone.timedelta(days=3)
    expiring_soon = Tenant.objects.filter(
        status='trial',
        trial_ends_at__lte=warning_date,
        trial_ends_at__gt=now,
    ).select_related('owner')

    warned = 0
    for tenant in expiring_soon:
        try:
            days_left = (tenant.trial_ends_at - now).days
            _send_trial_warning_email(tenant, days_left)
            warned += 1
        except Exception as e:
            logger.warning("Warning email failed for tenant %s: %s", tenant.id, e)

    logger.info("Trial check: %d expired, %d warned", expired_count, warned)
    return {"expired": expired_count, "warned": warned}


def _send_trial_warning_email(tenant, days_left):
    """Send trial expiry warning email to tenant admin."""
    from apps.accounts.models import User
    admin = User.objects.filter(tenant=tenant, is_superuser=True).first()
    if not admin or not admin.email:
        return

    app_url = getattr(settings, 'FRONTEND_URL', 'https://app.connectos.io')
    context = {
        'user_name': admin.get_full_name() or admin.email,
        'company_name': tenant.name,
        'days_remaining': days_left,
        'trial_ends_at': tenant.trial_ends_at.strftime('%B %d, %Y') if tenant.trial_ends_at else 'soon',
        'upgrade_url': f'{app_url}/settings/billing',
    }

    plural = 's' if days_left != 1 else ''
    subject = f'Your ConnectOS trial expires in {days_left} day{plural}'
    html_body = render_to_string('email/trial_expiry_warning.html', context)
    text_body = (
        f'Hi {context["user_name"]},\n\n'
        f'Your ConnectOS trial expires in {days_left} day{plural}.\n'
        f'Upgrade at: {context["upgrade_url"]}\n'
    )

    msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [admin.email])
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=True)


@shared_task(bind=True, max_retries=3)
def send_bulk_notification_email(self, tenant_id: str, subject: str,
                                  template: str, user_ids: list, context: dict):
    """Send a notification email to multiple users."""
    from apps.accounts.models import User
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    users = User.objects.filter(tenant_id=tenant_id, id__in=user_ids, is_active=True)
    sent = 0
    for user in users:
        try:
            ctx = {**context, 'user_name': user.get_full_name() or user.email}
            html = render_to_string(f'email/{template}.html', ctx)
            text = ctx.get('text_body', subject)
            msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [user.email])
            msg.attach_alternative(html, 'text/html')
            msg.send(fail_silently=True)
            sent += 1
        except Exception as e:
            logger.warning('Failed to send email to %s: %s', user.email, e)
    logger.info('Bulk email: sent %d/%d to tenant %s', sent, len(user_ids), tenant_id)
    return {'sent': sent, 'total': len(user_ids)}


@shared_task
def cleanup_expired_tokens():
    """Remove expired JWT tokens from the blacklist."""
    from django.utils import timezone
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        expired = OutstandingToken.objects.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        logger.info('Cleaned up %d expired JWT tokens', count)
        return count
    except Exception as e:
        logger.warning('Token cleanup failed: %s', e)
        return 0


@shared_task
def generate_tenant_report(tenant_id: str, report_type: str = 'summary') -> dict:
    """Generate a summary report for a tenant (async, result stored or emailed)."""
    from apps.candidates.models import Candidate
    from apps.jobs.models import Job
    from apps.applications.models import Application
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    month_ago = now - timedelta(days=30)
    report = {
        'tenant_id': tenant_id,
        'generated_at': now.isoformat(),
        'period': '30_days',
        'candidates': {
            'total': Candidate.objects.filter(tenant_id=tenant_id).count(),
            'new_this_month': Candidate.objects.filter(tenant_id=tenant_id, created_at__gte=month_ago).count(),
        },
        'jobs': {
            'total': Job.objects.filter(tenant_id=tenant_id).count(),
            'active': Job.objects.filter(tenant_id=tenant_id, status='published').count(),
        },
        'applications': {
            'total': Application.objects.filter(job__tenant_id=tenant_id).count(),
            'this_month': Application.objects.filter(job__tenant_id=tenant_id, created_at__gte=month_ago).count(),
        },
    }
    logger.info('Report generated for tenant %s', tenant_id)
    return report


@shared_task
def update_prometheus_gauges():
    """Update Prometheus gauge metrics."""
    try:
        from apps.shared.metrics import update_tenant_gauges
        update_tenant_gauges()
    except Exception as e:
        logger.debug('Metrics update failed (non-critical): %s', e)
