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
    from .enterprise import Subscription  # noqa: F401

    now = timezone.now()

    # Mark newly expired trials
    expired_count = Tenant.objects.filter(
        status='trial',
        trial_ends_at__lte=now,
    ).update(status='expired')

    # 3-day warning emails (#356)
    warning_3d = now + timezone.timedelta(days=3, hours=1)
    expiring_3d = Tenant.objects.filter(
        status='trial',
        trial_ends_at__lte=warning_3d,
        trial_ends_at__gt=now + timezone.timedelta(days=1, hours=12),
    ).select_related('owner')

    warned = 0
    for tenant in expiring_3d:
        try:
            _send_trial_warning_email(tenant, days_left=3)
            warned += 1
        except Exception as e:
            logger.warning("3-day warning email failed for tenant %s: %s", tenant.id, e)

    # 1-day warning emails (#356)
    warning_1d = now + timezone.timedelta(days=1, hours=1)
    expiring_1d = Tenant.objects.filter(
        status='trial',
        trial_ends_at__lte=warning_1d,
        trial_ends_at__gt=now,
    ).select_related('owner')

    for tenant in expiring_1d:
        try:
            _send_trial_warning_email(tenant, days_left=1)
            warned += 1
        except Exception as e:
            logger.warning("1-day warning email failed for tenant %s: %s", tenant.id, e)

    logger.info("Trial check: %d expired, %d warned", expired_count, warned)
    return {"expired": expired_count, "warned": warned}


def _send_trial_warning_email(tenant, days_left):
    """Send trial expiry warning email to tenant admin."""
    from authentication.models import User
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
def sync_employee_leave_balances():
    """Recalculate and sync leave balances for all active employees."""
    from core_hr.models import Employee
    from django.utils import timezone

    employees = Employee.objects.filter(
        is_active=True
    ).select_related('tenant')

    updated = 0
    for emp in employees.iterator(chunk_size=100):
        try:
            # Trigger balance recalculation if method exists
            if hasattr(emp, 'recalculate_leave_balance'):
                emp.recalculate_leave_balance()
                updated += 1
        except Exception as e:
            logger.warning('Leave balance sync failed for employee %s: %s', emp.id, e)

    logger.info('Leave balance sync completed: %d employees processed', updated)
    return updated


@shared_task
def update_prometheus_gauges():
    """Update Prometheus gauge metrics."""
    try:
        from core_hr.metrics import update_employee_gauge
        update_employee_gauge()
    except Exception as e:
        logger.debug('Metrics update failed (non-critical): %s', e)
