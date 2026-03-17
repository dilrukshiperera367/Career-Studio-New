"""ASGI config for ATS System."""

import os
import sentry_sdk
from django.core.asgi import get_asgi_application


def _init_sentry():
    dsn = os.environ.get('SENTRY_DSN', '')
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get('DJANGO_ENV', 'production'),
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            send_default_pii=False,
        )


_init_sentry()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
