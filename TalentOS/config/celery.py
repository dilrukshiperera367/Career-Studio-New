"""Celery configuration for ATS System."""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("ats")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


def _init_sentry_celery():
    dsn = os.environ.get('SENTRY_DSN', '')
    if dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get('DJANGO_ENV', 'production'),
        )


_init_sentry_celery()

# ---------------------------------------------------------------------------
# Periodic task schedule (Celery Beat)
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    "check-idle-applications": {
        "task": "apps.workflows.tasks.check_idle_applications",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
    },
    "compute-daily-analytics": {
        "task": "apps.analytics.tasks.compute_daily_analytics",
        "schedule": crontab(hour=3, minute=0),  # 03:00 UTC daily
    },
    "send-scheduled-messages": {
        "task": "apps.messaging.tasks.send_scheduled_messages",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "process-message-bounces": {
        "task": "apps.messaging.tasks.process_bounces",
        "schedule": crontab(hour="*/1", minute=15),  # Every hour at :15
    },
    "detect-stale-candidates": {
        "task": "apps.workflows.tasks.detect_stale_candidates",
        "schedule": crontab(hour=4, minute=0),  # 04:00 UTC daily
    },
    "refresh-search-index": {
        "task": "apps.search.tasks.refresh_search_index",
        "schedule": crontab(hour="*/6", minute=30),  # Every 6 hours at :30
    },
    "check-offer-expirations": {
        "task": "apps.workflows.tasks.check_offer_expirations",
        "schedule": crontab(hour=8, minute=0),  # 08:00 UTC daily
    },
    "generate-weekly-report": {
        "task": "apps.analytics.tasks.generate_weekly_report",
        "schedule": crontab(day_of_week=1, hour=6, minute=0),  # Monday 06:00
    },
    # Maintain audit_log monthly partitions (run first day of each month)
    "create-audit-log-partitions": {
        "task": "apps.shared.tasks.create_audit_log_partitions",
        "schedule": crontab(day_of_month=1, hour=0, minute=30),  # 1st of month 00:30 UTC
    },
    "check-trial-expirations": {
        "task": "tenants.check_trial_expirations",
        "schedule": crontab(hour=8, minute=0),  # daily at 08:00 UTC
    },
    'cleanup-expired-tokens': {
        'task': 'apps.tenants.tasks.cleanup_expired_tokens',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'update-metrics-gauges': {
        'task': 'apps.tenants.tasks.update_prometheus_gauges',
        'schedule': 60.0,  # Every 60 seconds
    },
    'auto-purge-expired-candidates': {
        'task': 'apps.consent.tasks.auto_purge_expired_candidates',
        'schedule': crontab(hour=2, minute=0),  # Daily at 02:00 UTC
    },
    'execute-pending-workflow-steps': {
        'task': 'apps.workflows.tasks.execute_pending_workflow_steps',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
