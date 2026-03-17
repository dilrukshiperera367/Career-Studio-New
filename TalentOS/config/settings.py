"""
Django settings for ATS System.
"""

import os
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

_secret_key = os.environ.get("DJANGO_SECRET_KEY", "")
if not _secret_key:
    if os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1"):
        import secrets as _secrets
        _secret_key = "django-insecure-dev-" + _secrets.token_hex(32)
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY environment variable is not set. "
            "Set it to a long random string before deploying."
        )
SECRET_KEY = _secret_key

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

# Cookie security (explicit — aligns with Django 3.1+ defaults but documented)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# HTTPS settings (active in production)
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_HSTS_SECONDS = int(os.environ.get('HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('HSTS_SECONDS', '0') != '0'
SECURE_HSTS_PRELOAD = os.environ.get('HSTS_SECONDS', '0') != '0'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_celery_beat",
    # ATS apps
    "apps.tenants",
    "apps.accounts",
    "apps.jobs",
    "apps.candidates",
    "apps.applications",
    "apps.taxonomy",
    "apps.workflows",
    "apps.messaging",
    "apps.analytics",
    "apps.consent",
    "apps.parsing",
    "apps.search",
    "apps.portal",
    "apps.scoring",
    "apps.blog",
    "apps.notifications",
    "apps.shared",
    # New TalentOS Hiring Cloud apps
    "apps.job_architecture",
    "apps.compensation_ops",
    "apps.talent_crm",
    "apps.referrals",
    "apps.assessments",
    "apps.vendor_management",
    "apps.recruitment_marketing",
    "apps.trust_ops",
    "apps.compliance_ai",
    "apps.internal_recruiting",
    "apps.analytics_forecasting",
    "apps.accessibility_ops",
    "apps.sourcing_crm",
    "apps.interview_ops",
    "apps.hm_workspace",
    "apps.comp_ops",
    "apps.internal_bridge",
    # ConnectOS platform shared layer
    "platform_auth",
    "platform_person",
    "platform_organization",
    "platform_skills",
    "platform_jobs",
    "platform_trust",
    "platform_events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.shared.security_middleware.SecurityHeadersMiddleware",
    "apps.shared.security_middleware.RateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenants.middleware.TenantMiddleware",
    "apps.tenants.middleware.TrialEnforcementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Logging, audit, and CORS validation
    "apps.shared.middleware.RequestLoggingMiddleware",
    "apps.shared.middleware.LoginThrottleMiddleware",
    "apps.shared.audit_middleware.AuditLogMiddleware",
    "apps.shared.audit_middleware.CORSValidationMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL with RLS
# ---------------------------------------------------------------------------

# Use PostgreSQL if POSTGRES_DB env var is set, otherwise fall back to SQLite for dev
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "ats_db"),
            "USER": os.environ.get("POSTGRES_USER", "ats_user"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "ats_password"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "OPTIONS": {
                "options": "-c statement_timeout=30000",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "apps.shared.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.shared.throttling.BurstUserThrottle",
        "apps.shared.throttling.AuthenticatedUserThrottle",
        "apps.shared.throttling.AnonymousUserThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/hour",
        "anon": "60/hour",
        "burst": "60/min",
        "tenant": "500/min",
        "login": "5/minute",
    },
}

# API Documentation (drf-spectacular)
SPECTACULAR_SETTINGS = {
    'TITLE': 'ConnectOS ATS API',
    'DESCRIPTION': 'Applicant Tracking System API for ConnectOS platform.',
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

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

_jwt_signing_key = os.environ.get("SHARED_JWT_SECRET", "")
if not _jwt_signing_key:
    if not DEBUG:
        raise RuntimeError(
            "SHARED_JWT_SECRET environment variable must be set in production."
        )
    _jwt_signing_key = SECRET_KEY  # dev-only fallback

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": _jwt_signing_key,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.TokenObtainSerializer",
}

# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Task Processing (Celery)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {
    # Trial lifecycle
    "check-trial-expiry-daily": {
        "task": "apps.shared.tasks.check_trial_expiry",
        "schedule": crontab(hour=6, minute=0),
    },
    "check-trial-expirations-daily": {
        "task": "tenants.check_trial_expirations",
        "schedule": crontab(hour=6, minute=30),
    },
    # Job lifecycle (#58)
    "auto-close-stale-jobs-daily": {
        "task": "apps.jobs.tasks.auto_close_stale_jobs",
        "schedule": crontab(hour=1, minute=0),
    },
    # Interview reminders (#59) — run every 30 minutes
    "send-interview-reminders": {
        "task": "apps.jobs.tasks.send_interview_reminders",
        "schedule": crontab(minute="*/30"),
    },
    # Daily analytics (#60)
    "compute-daily-analytics": {
        "task": "apps.analytics.tasks.compute_daily_analytics",
        "schedule": crontab(hour=2, minute=0),
    },
    # Candidate data retention (#61) — weekly Sunday at 03:00
    "enforce-candidate-retention-weekly": {
        "task": "apps.jobs.tasks.enforce_candidate_retention",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),
    },
    # OpenSearch index sync (#62) — every hour
    "refresh-search-index-hourly": {
        "task": "apps.search.tasks.refresh_search_index",
        "schedule": crontab(minute=15),
    },
    # Workflow automation
    "execute-pending-workflow-steps": {
        "task": "apps.workflows.tasks.execute_pending_workflow_steps",
        "schedule": crontab(minute="*/5"),
    },
    "check-idle-applications-daily": {
        "task": "apps.workflows.tasks.check_idle_applications",
        "schedule": crontab(hour=7, minute=0),
    },
    # Audit log partition maintenance — monthly
    "audit-log-partition-monthly": {
        "task": "apps.shared.tasks.create_audit_log_partitions",
        "schedule": crontab(day_of_month=1, hour=0, minute=30),
    },
    # Cross-system ATS↔HRM drift reconciliation (#310) — removed pending ats app implementation
    # GDPR consent expiry (#57) — daily at 04:00
    "expire-old-consent-records-daily": {
        "task": "apps.consent.tasks.expire_old_consent_records",
        "schedule": crontab(hour=4, minute=0),
    },
    # GDPR candidate hard-delete (#61 grace period) — daily at 03:30
    "auto-purge-expired-candidates-daily": {
        "task": "apps.consent.tasks.auto_purge_expired_candidates",
        "schedule": crontab(hour=3, minute=30),
    },
    # Assessments
    "send-assessment-reminders": {
        "task": "apps.assessments.tasks.send_assessment_reminders",
        "schedule": crontab(hour="*/6"),
    },
    "expire-stale-assessment-orders": {
        "task": "apps.assessments.tasks.expire_stale_assessment_orders",
        "schedule": crontab(hour=2, minute=0),
    },
    # Vendor management
    "check-vendor-sla-compliance": {
        "task": "apps.vendor_management.tasks.check_vendor_sla_compliance",
        "schedule": crontab(hour=7, minute=0),
    },
    "generate-vendor-scorecards-monthly": {
        "task": "apps.vendor_management.tasks.generate_vendor_scorecards",
        "schedule": crontab(day_of_month=1, hour=3),
    },
    # Recruitment marketing
    "publish-scheduled-social-posts": {
        "task": "apps.recruitment_marketing.tasks.publish_scheduled_social_posts",
        "schedule": crontab(minute=0),
    },
    "aggregate-utm-stats-daily": {
        "task": "apps.recruitment_marketing.tasks.aggregate_utm_stats",
        "schedule": crontab(hour=1, minute=30),
    },
    # Trust ops
    "scan-pending-documents": {
        "task": "apps.trust_ops.tasks.scan_pending_documents",
        "schedule": crontab(minute="*/15"),
    },
    "expire-safe-share-links": {
        "task": "apps.trust_ops.tasks.expire_safe_share_links",
        "schedule": crontab(hour=3, minute=0),
    },
    # Compliance AI
    "escalate-overdue-ai-reviews": {
        "task": "apps.compliance_ai.tasks.escalate_overdue_reviews",
        "schedule": crontab(hour=8, minute=0),
    },
    "expire-ai-logs-daily": {
        "task": "apps.compliance_ai.tasks.expire_ai_logs",
        "schedule": crontab(hour=4, minute=0),
    },
    # Internal recruiting
    "close-expired-internal-windows": {
        "task": "apps.internal_recruiting.tasks.close_expired_internal_windows",
        "schedule": crontab(hour=0, minute=30),
    },
    "notify-employees-internal-postings": {
        "task": "apps.internal_recruiting.tasks.notify_employees_of_internal_postings",
        "schedule": crontab(hour=9, minute=0),
    },
    # Analytics forecasting
    "compute-fill-time-forecasts-daily": {
        "task": "apps.analytics_forecasting.tasks.compute_fill_time_forecasts",
        "schedule": crontab(hour=5, minute=0),
    },
    "detect-pipeline-bottlenecks-daily": {
        "task": "apps.analytics_forecasting.tasks.detect_pipeline_bottlenecks",
        "schedule": crontab(hour=6, minute=0),
    },
    "generate-fairness-reports-weekly": {
        "task": "apps.analytics_forecasting.tasks.generate_fairness_reports",
        "schedule": crontab(day_of_week=1, hour=5, minute=30),
    },
    # Accessibility ops
    "flag-overdue-accessibility-reviews": {
        "task": "apps.accessibility_ops.tasks.flag_overdue_accessibility_reviews",
        "schedule": crontab(hour=7, minute=30),
    },
    # ConnectOS platform — consume Redis Streams events every 5 s
    "platform-consume-streams": {
        "task": "platform_events.consumer.consume_streams",
        "schedule": 5.0,  # seconds
    },
}

# ---------------------------------------------------------------------------
# ConnectOS — event handler registry
# ---------------------------------------------------------------------------
PLATFORM_EVENT_HANDLERS = {
    "application.submitted": "apps.accounts.event_handlers.on_application_submitted",
    "job.posted":            "apps.accounts.event_handlers.on_job_posted_broadcast",
    "employee.offboarded":   "apps.accounts.event_handlers.on_employee_offboarded",
}

# ---------------------------------------------------------------------------
# Object Storage (S3-compatible)
# ---------------------------------------------------------------------------

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "ats-resumes")
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", "http://localhost:9000")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
AWS_DEFAULT_ACL = "private"
AWS_S3_FILE_OVERWRITE = False

# Use S3/MinIO for file media when USE_S3 env var is set (production).
# Falls back to local FileSystemStorage in development.
_use_s3 = os.environ.get("USE_S3", "false").lower() == "true"
STORAGES = {
    "default": {
        "BACKEND": (
            "storages.backends.s3boto3.S3Boto3Storage"
            if _use_s3
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# OpenSearch
# ---------------------------------------------------------------------------

OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", "9200"))
OPENSEARCH_USE_SSL = os.environ.get("OPENSEARCH_USE_SSL", "false").lower() == "true"
OPENSEARCH_HTTP_AUTH = (
    os.environ.get("OPENSEARCH_USER", "admin"),
    os.environ.get("OPENSEARCH_PASSWORD", "admin"),
)

# ---------------------------------------------------------------------------
# Email — console backend in dev, SMTP override per-tenant at runtime
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@connectos.io")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://app.connectos.io")

# ---------------------------------------------------------------------------
# Resume parsing
# ---------------------------------------------------------------------------

RESUME_MAX_SIZE_MB = 10
RESUME_ALLOWED_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
RESUME_MIN_TEXT_CHARS = 300
SPACY_MODEL = "en_core_web_sm"

# ---------------------------------------------------------------------------
# ATS Business Config
# ---------------------------------------------------------------------------

IDLE_THRESHOLD_DAYS = 7
CANDIDATE_DEDUP_AUTO_THRESHOLD = 0.92
CANDIDATE_DEDUP_FLAG_THRESHOLD = 0.85
CANDIDATE_DEDUP_LOOKBACK_DAYS = 365

# Ranking weights
RANKING_WEIGHTS = {
    "hybrid": {
        "text_norm": 0.55,
        "skill_match": 0.30,
        "title_match": 0.10,
        "recency": 0.05,
    },
    "structured": {
        "skill_match": 0.45,
        "title_match": 0.20,
        "domain_match": 0.15,
        "experience_fit": 0.10,
        "recency": 0.10,
    },
}

# Recency decay
RECENCY_DECAY_FACTOR = 0.35

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Caching — Redis (#153-156)
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
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
        'KEY_PREFIX': 'ats',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Dashboard metrics cache: 5 min
DASHBOARD_CACHE_TTL = 300
# Analytics cache: 1 hour
ANALYTICS_CACHE_TTL = 3600
# Search facet cache: 10 min
SEARCH_FACET_CACHE_TTL = 600

# ---------------------------------------------------------------------------
# Sessions — Redis-backed (#153)
# ---------------------------------------------------------------------------

SESSION_ENGINE = "django.contrib.sessions.backends.cache" if not DEBUG else "django.contrib.sessions.backends.db"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_TIMEOUT", 3600))  # 1 hour default
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ---------------------------------------------------------------------------
# Database tuning (#165)
# ---------------------------------------------------------------------------

CONN_MAX_AGE = int(os.environ.get("CONN_MAX_AGE", 600))
CONN_HEALTH_CHECKS = True

# ---------------------------------------------------------------------------
# Structured Logging — JSON format in production (#232)
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": (
            {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
            if os.getenv("USE_JSON_LOGGING", "false").lower() == "true"
            else {
                "format": "{levelname} {asctime} {name} {message}",
                "style": "{",
            }
        ),
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "ats.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        },
        "audit_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "audit.log",
            "maxBytes": 1024 * 1024 * 20,  # 20 MB
            "backupCount": 10,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file", "mail_admins"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "file", "mail_admins"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.audit": {
            "handlers": ["audit_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# ---------------------------------------------------------------------------
# CORS (#122) — hardened for production
# ---------------------------------------------------------------------------

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
CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type",
    "dnt", "origin", "user-agent", "x-csrftoken", "x-requested-with",
    "x-correlation-id",
]

# ---------------------------------------------------------------------------
# CSRF Protection (#110)
# ---------------------------------------------------------------------------

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

# ---------------------------------------------------------------------------
# Sentry Error Tracking
# ---------------------------------------------------------------------------

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            RedisIntegration(),
        ],
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        release=os.environ.get("APP_VERSION", "unknown"),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.05")),
        send_default_pii=False,
    )

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

INSTALLED_APPS += ["django_prometheus"]
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
] + MIDDLEWARE + [
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# ---------------------------------------------------------------------------
# Cross-System Auth — Shared JWT
# ---------------------------------------------------------------------------

# If SHARED_JWT_SECRET is set, both ATS and HRM use the same signing key
# so a token issued by either system works in both.
SHARED_JWT_SECRET = os.environ.get("SHARED_JWT_SECRET", "")
if SHARED_JWT_SECRET:
    SIMPLE_JWT["SIGNING_KEY"] = SHARED_JWT_SECRET

# Module switcher — JWT payload includes active_product claim
# ATS sets: {"active_product": "ats"} | HRM sets: {"active_product": "hrm"}
ATS_PRODUCT_CLAIM = "ats"
HRM_BASE_URL = os.environ.get("HRM_BASE_URL", "http://localhost:5173")

# ---------------------------------------------------------------------------
# ClamAV Antivirus Integration
# ---------------------------------------------------------------------------

CLAMAV_HOST = os.environ.get("CLAMAV_HOST", "clamav")
CLAMAV_PORT = int(os.environ.get("CLAMAV_PORT", "3310"))
CLAMAV_ENABLED = os.environ.get("CLAMAV_ENABLED", "True" if not DEBUG else "False").lower() in ("true", "1")
CLAMAV_TIMEOUT = int(os.environ.get("CLAMAV_TIMEOUT", "30"))
# Strict mode: reject file if ClamAV is unreachable or returns unexpected response.
# Defaults to True in production, False in DEBUG.  Override via CLAMAV_STRICT_MODE env var.
CLAMAV_STRICT_MODE = os.environ.get("CLAMAV_STRICT_MODE", "True" if not DEBUG else "False").lower() in ("true", "1")

# ---------------------------------------------------------------------------
# Security Hardening (production)
# ---------------------------------------------------------------------------

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
