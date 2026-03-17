"""
Django settings for ConnectHR HRM System.
"""

import os
from pathlib import Path
from datetime import timedelta
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security ---
_secret_key = os.getenv('DJANGO_SECRET_KEY', '')
if not _secret_key:
    if os.getenv('DJANGO_DEBUG', 'True').lower() == 'true':
        import secrets as _secrets
        _secret_key = 'django-insecure-dev-' + _secrets.token_hex(32)
    else:
        raise RuntimeError(
            'DJANGO_SECRET_KEY environment variable is not set. '
            'Set it to a long random string before deploying.'
        )
SECRET_KEY = _secret_key

DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Cookie security (explicit)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# --- Security Headers ---
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# HTTPS settings (active in production)
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_HSTS_SECONDS = int(os.getenv('HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_SECONDS', '0') != '0'
SECURE_HSTS_PRELOAD = os.getenv('HSTS_SECONDS', '0') != '0'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- Application Definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_extensions',
    'django_celery_beat',
    'drf_spectacular',
    'simple_history',

    # HRM Apps
    'tenants',
    'authentication',
    'core_hr',
    'leave_attendance',
    'payroll',
    'onboarding',
    'performance',
    'analytics',
    'integrations',
    'platform_core',
    'engagement',
    'learning',
    'helpdesk',
    'workflows',
    'custom_objects',

    # WorkforceOS expansion apps
    'manager_hub',
    'employee_hub',
    'internal_marketplace',
    'total_rewards',
    'employee_relations',
    'people_analytics',
    'compliance_ai',
    'workforce_planning',
    'documents_policies',
    'experience_hub',
    'global_workforce',
    'contingent_ops',
    # ConnectOS platform shared layer
    'platform_auth',
    'platform_person',
    'platform_organization',
    'platform_skills',
    'platform_jobs',
    'platform_trust',
    'platform_events',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'platform_core.security_middleware.SecurityHeadersMiddleware',
    'platform_core.security_middleware.RateLimitMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    # Custom HRM middleware
    'tenants.middleware.TenantMiddleware',
    'tenants.middleware.TrialEnforcementMiddleware',
    'platform_core.middleware.AuditMiddleware',
    'platform_core.audit_middleware.AuditLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- Database ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'hrm_db'),
        'USER': os.getenv('DB_USER', 'hrm_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'hrm_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 5,
        },
        'TEST': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        },
    }
}

# Use SQLite for development if PostgreSQL is not available
if os.getenv('USE_SQLITE', 'false').lower() == 'true':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --- Custom User Model ---
AUTH_USER_MODEL = 'authentication.User'

# --- Password Validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Colombo'
USE_I18N = True
USE_TZ = True

# --- Static & Media ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Django REST Framework ---
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'platform_core.exceptions.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'authentication.throttling.BurstUserThrottle',
        'authentication.throttling.AuthenticatedUserThrottle',
        'authentication.throttling.AnonymousUserThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/hour',
        'anon': '60/hour',
        'burst': '60/min',
        'tenant': '500/min',
        'login': '5/minute',
    },
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
    'DATE_FORMAT': '%Y-%m-%d',
}

# --- JWT ---
_jwt_signing_key = os.getenv('SHARED_JWT_SECRET', '')
if not _jwt_signing_key:
    if not DEBUG:
        raise RuntimeError(
            'SHARED_JWT_SECRET environment variable must be set in production.'
        )
    _jwt_signing_key = SECRET_KEY  # dev-only fallback

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': _jwt_signing_key,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# --- Stripe ---
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICE_ID_MONTHLY = os.environ.get('STRIPE_PRICE_ID_MONTHLY', '')
STRIPE_PRICE_ID_ANNUAL = os.environ.get('STRIPE_PRICE_ID_ANNUAL', '')
STRIPE_PRICE_STARTER_MONTHLY = os.environ.get('STRIPE_PRICE_STARTER_MONTHLY', '')
STRIPE_PRICE_STARTER_ANNUAL = os.environ.get('STRIPE_PRICE_STARTER_ANNUAL', '')
STRIPE_PRICE_PRO_MONTHLY = os.environ.get('STRIPE_PRICE_PRO_MONTHLY', '')
STRIPE_PRICE_PRO_ANNUAL = os.environ.get('STRIPE_PRICE_PRO_ANNUAL', '')
STRIPE_PRICE_ENTERPRISE_MONTHLY = os.environ.get('STRIPE_PRICE_ENTERPRISE_MONTHLY', '')
STRIPE_PRICE_ENTERPRISE_ANNUAL = os.environ.get('STRIPE_PRICE_ENTERPRISE_ANNUAL', '')

if STRIPE_SECRET_KEY:
    import stripe as _stripe
    _stripe.api_key = STRIPE_SECRET_KEY

# --- CORS ---
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://app.connectos.io",
    "https://hrm.connectos.io",
    "https://connectos.io",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Ensure this is False

# --- Celery ---
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Colombo'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Periodic task schedule (synced to DB on startup by celery beat)
CELERY_BEAT_SCHEDULE = {
    'check-expiring-documents-daily': {
        'task': 'core_hr.tasks.check_expiring_documents',
        'schedule': crontab(hour=5, minute=0),
    },
    'certification-expiry-alerts-daily': {
        'task': 'payroll.tasks.certification_expiry_alerts',
        'schedule': crontab(hour=5, minute=15),
    },
    'leave-accrual-monthly': {
        'task': 'leave_attendance.tasks.run_monthly_leave_accrual',
        'schedule': crontab(hour=0, minute=30),  # daily; task gates on last-day-of-month
    },
    'check-trial-expirations': {
        'task': 'tenants.tasks.check_trial_expirations',
        'schedule': crontab(hour=8, minute=0),
    },
    # #151 — Attendance auto clock-out
    'attendance-auto-clock-out-nightly': {
        'task': 'leave_attendance.tasks.attendance_auto_clock_out',
        'schedule': crontab(hour=23, minute=50),
    },
    # #153 — Payroll reminders
    'payroll-reminder-monthly': {
        'task': 'payroll.tasks.send_payroll_reminders',
        'schedule': crontab(hour=9, minute=0),  # daily; task gates on day=23
    },
    # #154 — Performance review notifications
    'performance-review-notifications-daily': {
        'task': 'performance.tasks.send_performance_review_notifications',
        'schedule': crontab(hour=8, minute=30),
    },
    # #155 — Onboarding task reminders
    'onboarding-task-reminders-daily': {
        'task': 'onboarding.tasks.send_onboarding_task_reminders',
        'schedule': crontab(hour=8, minute=45),
    },
    # #156 — Probation period alerts
    'probation-period-alerts-daily': {
        'task': 'core_hr.tasks.send_probation_period_alerts',
        'schedule': crontab(hour=9, minute=15),
    },
    # #157 — Document expiry alerts (already in core_hr.tasks.check_expiring_documents)
    # #158 — Birthday / anniversary (already in workflows.tasks)
    'send-birthday-greetings-daily': {
        'task': 'workflows.tasks.send_birthday_greetings',
        'schedule': crontab(hour=7, minute=0),
    },
    'send-anniversary-greetings-daily': {
        'task': 'workflows.tasks.send_work_anniversary_greetings',
        'schedule': crontab(hour=7, minute=5),
    },
    # Workflow due-events scan every 5 minutes
    'process-due-workflow-events': {
        'task': 'workflows.tasks.process_due_workflow_events',
        'schedule': crontab(minute='*/5'),
    },

    # --- WorkforceOS expansion app periodic tasks ---
    # people_analytics — weekly attrition risk score computation (Sundays 01:00)
    'compute-attrition-risk-weekly': {
        'task': 'people_analytics.tasks.compute_attrition_risk_scores',
        'schedule': crontab(hour=1, minute=0, day_of_week=0),
    },
    # people_analytics — monthly headcount snapshot (1st of month 01:30)
    'headcount-snapshot-monthly': {
        'task': 'people_analytics.tasks.generate_headcount_snapshot',
        'schedule': crontab(hour=1, minute=30, day_of_month=1),
    },
    # global_workforce — daily visa/permit expiry reminders (06:00)
    'visa-permit-expiry-reminders-daily': {
        'task': 'global_workforce.tasks.send_visa_permit_expiry_reminders',
        'schedule': crontab(hour=6, minute=0),
    },
    # total_rewards — daily merit cycle deadline reminders (08:00)
    'merit-cycle-deadline-reminders-daily': {
        'task': 'total_rewards.tasks.send_merit_cycle_deadline_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    # documents_policies — weekly policy acknowledgement reminders (Mon 09:00)
    'policy-acknowledgement-reminders-weekly': {
        'task': 'documents_policies.tasks.send_policy_acknowledgement_reminders',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    # ConnectOS platform — consume Redis Streams events every 5 s
    'platform-consume-streams': {
        'task': 'platform_events.consumer.consume_streams',
        'schedule': 5.0,  # seconds
    },
}

# ---------------------------------------------------------------------------
# ConnectOS — event handler registry
# ---------------------------------------------------------------------------
PLATFORM_EVENT_HANDLERS = {
    'application.offer_accepted': 'authentication.event_handlers.on_offer_accepted',
    'employee.offboarded':        'authentication.event_handlers.on_employee_offboarded',
    'person.created':             'authentication.event_handlers.on_person_created',
}

# --- Object Storage (S3/MinIO) ---
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'hrm-documents')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', '')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'private'

# --- drf-spectacular (OpenAPI/Swagger) ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'ConnectOS HRM API',
    'DESCRIPTION': 'HRM SaaS Platform REST API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'SECURITY': [{'bearerAuth': []}],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
}

# --- Email ---
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@connectos.io')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://app.connectos.io')

# --- ATS Integration ---
ATS_WEBHOOK_SECRET = os.getenv('ATS_WEBHOOK_SECRET', '')
ATS_BASE_URL = os.getenv('ATS_BASE_URL', 'http://localhost:8000')

# --- Cache (Redis) ---
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,  # Don't crash if Redis is down
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'hrm',
        'TIMEOUT': 300,  # 5 minutes default
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# --- Sentry Error Tracking ---
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style='url'),
            CeleryIntegration(monitor_beat_tasks=True),
            RedisIntegration(),
        ],
        environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
        release=os.getenv('APP_VERSION', 'unknown'),
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        send_default_pii=False,
    )

# --- Prometheus Metrics ---
INSTALLED_APPS += ['django_prometheus']
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
] + MIDDLEWARE + [
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# --- Cross-System Auth — Shared JWT ---
# If SHARED_JWT_SECRET is set, ATS and HRM use the identical signing key
# so tokens issued by either system are accepted in both.
SHARED_JWT_SECRET = os.getenv('SHARED_JWT_SECRET', '')
if SHARED_JWT_SECRET:
    SIMPLE_JWT['SIGNING_KEY'] = SHARED_JWT_SECRET

# ConnectOS platform portal identity
PLATFORM_PORTAL_NAME = 'workforceos'
WORKFORCEOS_BASE_URL = os.getenv('WORKFORCEOS_BASE_URL', 'http://localhost:8006')

# HRM module claim for module switcher
HRM_PRODUCT_CLAIM = 'hrm'
ATS_BASE_URL_FRONTEND = os.getenv('ATS_BASE_URL_FRONTEND', 'http://localhost:3000')

# --- ClamAV Antivirus Integration ---
CLAMAV_HOST = os.getenv('CLAMAV_HOST', 'clamav')
CLAMAV_PORT = int(os.getenv('CLAMAV_PORT', '3310'))
CLAMAV_ENABLED = os.getenv('CLAMAV_ENABLED', 'True' if not DEBUG else 'False').lower() in ('true', '1')
CLAMAV_TIMEOUT = int(os.getenv('CLAMAV_TIMEOUT', '30'))
# Strict mode: reject file if ClamAV is unreachable or returns unexpected response.
# Defaults to True in production, False in DEBUG.
CLAMAV_STRICT_MODE = os.getenv('CLAMAV_STRICT_MODE', 'True' if not DEBUG else 'False').lower() in ('true', '1')

# --- Security Hardening (production) ---
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# --- Logging ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'hrm': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'hrm.audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
