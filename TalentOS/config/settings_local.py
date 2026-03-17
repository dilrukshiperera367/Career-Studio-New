"""
Local settings override — uses SQLite when Docker services aren't available.
"""

from config.settings import *  # noqa

# Override database to SQLite for local testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Disable OpenSearch for local testing
OPENSEARCH_HOST = None

# Use console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable Celery (run tasks synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
