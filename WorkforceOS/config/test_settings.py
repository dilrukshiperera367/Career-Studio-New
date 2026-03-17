"""
Test settings — inherits from main settings but uses SQLite in-memory.
Used by pytest via pytest.ini DJANGO_SETTINGS_MODULE override.
"""

from config.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable email sending in tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Use in-memory cache (avoids Redis connection hang during tests)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use DB-backed sessions (avoids Redis dependency)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Use in-memory broker so Celery never tries to connect to Redis during tests
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Disable Celery task execution (run tasks eagerly / synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
