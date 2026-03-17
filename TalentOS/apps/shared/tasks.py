"""Celery task retry configuration — max retries and exponential backoff for all tasks."""

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


# ---------------------------------------------------------------------------
# Trial expiry management task
# ---------------------------------------------------------------------------

@shared_task(name='apps.shared.tasks.check_trial_expiry')
def check_trial_expiry():
    """Daily task: expire trials, start grace periods, and notify users."""
    from apps.accounts.models import Subscription
    from django.utils import timezone

    now = timezone.now()

    # Expire trials that have ended — move into grace period
    expired = Subscription.objects.filter(
        status='trialing',
        trial_end__lte=now,
    )
    count = 0
    for sub in expired:
        sub.expire_trial()
        count += 1
        try:
            _send_trial_expired_email(sub.tenant)
        except Exception:
            pass

    # Fully expire grace periods that have ended
    grace_expired_qs = Subscription.objects.filter(
        status='grace_period',
        grace_period_end__lte=now,
    )
    grace_expired_count = grace_expired_qs.count()
    for sub in grace_expired_qs:
        sub.status = 'expired'
        sub.save(update_fields=['status', 'updated_at'])

    # 3-day trial warning emails
    warning_3d = Subscription.objects.filter(
        status='trialing',
        trial_end__date=(now + timezone.timedelta(days=3)).date(),
    )
    for sub in warning_3d:
        try:
            _send_trial_warning_email(sub.tenant, days_remaining=3)
        except Exception:
            pass

    # 1-day trial warning emails
    warning_1d = Subscription.objects.filter(
        status='trialing',
        trial_end__date=(now + timezone.timedelta(days=1)).date(),
    )
    for sub in warning_1d:
        try:
            _send_trial_warning_email(sub.tenant, days_remaining=1)
        except Exception:
            pass

    logger.info('Trial expiry check: %d expired, %d grace expired', count, grace_expired_count)
    return {'expired': count, 'grace_expired': grace_expired_count}


def _send_trial_warning_email(tenant, days_remaining):
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.accounts.models import User
    admins = User.objects.filter(tenant=tenant, user_type='company_admin', is_active=True)
    plural = 's' if days_remaining != 1 else ''
    for admin in admins:
        send_mail(
            subject=f'Your ConnectOS trial ends in {days_remaining} day{plural}',
            message=(
                f'Dear {admin.first_name},\n\n'
                f'Your ConnectOS free trial expires in {days_remaining} day{plural}. '
                f'Upgrade now to keep your data.\n\n'
                f'Upgrade: https://app.connectos.io/billing/\n\nTeam ConnectOS'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@connectos.io'),
            recipient_list=[admin.email],
            fail_silently=True,
        )


def _send_trial_expired_email(tenant):
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.accounts.models import User
    admins = User.objects.filter(tenant=tenant, user_type='company_admin', is_active=True)
    for admin in admins:
        send_mail(
            subject='Your ConnectOS trial has expired',
            message=(
                f'Dear {admin.first_name},\n\n'
                f'Your ConnectOS trial has expired. You have a 3-day grace period to upgrade.\n\n'
                f'Upgrade: https://app.connectos.io/billing/\n\nTeam ConnectOS'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@connectos.io'),
            recipient_list=[admin.email],
            fail_silently=True,
        )

DEFAULT_RETRY_KWARGS = {
    "max_retries": 3,
    "countdown": 60,  # 1 min initial delay
    "retry_backoff": True,  # Exponential backoff
    "retry_backoff_max": 600,  # Max 10 min between retries
    "retry_jitter": True,  # Add random jitter to prevent thundering herd
}


@shared_task(bind=True, **DEFAULT_RETRY_KWARGS, name="apps.shared.tasks.send_webhook_task")
def send_webhook_task(self, url, payload, secret=None):
    """Send webhook with retry and exponential backoff."""
    try:
        from apps.shared.advanced_api import deliver_webhook
        result = deliver_webhook(url, payload, secret, max_retries=1)
        if result["status"] == "failed":
            raise Exception(f"Webhook delivery failed to {url}")
        return result
    except Exception as exc:
        logger.warning(f"Webhook task retry {self.request.retries}/{self.max_retries}: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, **DEFAULT_RETRY_KWARGS, name="apps.shared.tasks.send_email_task")
def send_email_task(self, to_email, subject, body, from_email=None):
    """Send email with retry."""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return {"status": "sent", "to": to_email}
    except Exception as exc:
        logger.warning(f"Email task retry {self.request.retries}/{self.max_retries}: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, countdown=120, retry_backoff=True, name="apps.shared.tasks.bulk_score_task")
def bulk_score_task(self, candidate_ids, job_id):
    """Bulk score candidates with retry."""
    try:
        from apps.scoring.services import score_candidates
        results = score_candidates(candidate_ids, job_id)
        logger.info(f"Scored {len(results)} candidates for job {job_id}")
        return {"scored": len(results), "job_id": str(job_id)}
    except Exception as exc:
        logger.warning(f"Bulk score retry {self.request.retries}/{self.max_retries}: {exc}")
        self.retry(exc=exc)


@shared_task(name="apps.shared.tasks.create_audit_log_partitions")
def create_audit_log_partitions():
    """
    Monthly Celery Beat task: ensure the ats_audit_log partitioned table
    has partitions for the next 3 months.  Safe to run multiple times —
    all CREATE TABLE calls are IF NOT EXISTS.
    """
    from django.db import connection

    sql = """
    DO $$
    DECLARE
        start_date  date := date_trunc('month', now())::date;
        months      int  := 3;
        d           date;
        tname       text;
        end_date    date;
    BEGIN
        FOR i IN 0..months - 1 LOOP
            d        := start_date + (i || ' months')::interval;
            end_date := d + '1 month'::interval;
            tname    := 'ats_audit_log_' || to_char(d, 'YYYY_MM');

            IF NOT EXISTS (
                SELECT 1 FROM pg_tables WHERE tablename = tname
            ) THEN
                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF ats_audit_log
                        FOR VALUES FROM (%L) TO (%L)',
                    tname, d, end_date
                );
                RAISE NOTICE 'Created partition: %', tname;
            END IF;
        END LOOP;
    END $$;
    """

    try:
        with connection.cursor() as cur:
            cur.execute(sql)
        logger.info('audit_log partition maintenance completed')
        return {'status': 'ok'}
    except Exception as exc:
        logger.error('audit_log partition maintenance failed: %s', exc)
        return {'status': 'error', 'error': str(exc)}

