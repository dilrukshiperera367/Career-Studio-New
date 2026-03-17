"""Celery application configuration for ConnectHR."""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('connecthr')
app.config_from_object('django.conf:settings', namespace='CELERY')
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


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


from celery.schedules import crontab  # noqa: E402

app.conf.beat_schedule = {
    'cleanup-expired-tokens': {
        'task': 'tenants.tasks.cleanup_expired_tokens',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'sync-leave-balances': {
        'task': 'tenants.tasks.sync_employee_leave_balances',
        'schedule': crontab(hour=1, minute=0, day_of_week=1),  # Weekly Monday 1 AM
    },
    'update-metrics-gauges': {
        'task': 'tenants.tasks.update_prometheus_gauges',
        'schedule': 60.0,
    },
}
