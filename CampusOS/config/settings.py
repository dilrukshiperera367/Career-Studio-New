"""
CampusOS — Django Settings
Education-to-Employment Operating System
"""

import os
from datetime import timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-campusos-dev-key-change-in-production")

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.campus",
    "apps.students",
    "apps.readiness",
    "apps.internships",
    "apps.placements",
    "apps.campus_employers",
    "apps.campus_events",
    "apps.alumni_mentors",
    "apps.credentials_wallet",
    "apps.outcomes_analytics",
    "apps.advisors",
    "apps.assessments",
    "apps.campus_trust",
    "apps.campus_integrations",
    "apps.billing",
    "apps.analytics",
    "apps.shared",
    # ConnectOS platform shared layer
    "platform_auth",
    "platform_person",
    "platform_organization",
    "platform_skills",
    "platform_jobs",
    "platform_trust",
    "platform_events",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
    },
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

# ── Platform identity ────────────────────────────────────────────────────────
PLATFORM_PORTAL_NAME = "campusos"
CAMPUSOS_BASE_URL = os.environ.get("CAMPUSOS_BASE_URL", "http://localhost:5174")

_jwt_signing_key = os.environ.get("SHARED_JWT_SECRET", "")
if not _jwt_signing_key:
    if not DEBUG:
        raise RuntimeError(
            "SHARED_JWT_SECRET environment variable must be set in production."
        )
    _jwt_signing_key = SECRET_KEY

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": _jwt_signing_key,
    "TOKEN_OBTAIN_SERIALIZER": "platform_auth.cross_auth.PlatformTokenObtainSerializer",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")

CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# DRF Spectacular (OpenAPI)
# ---------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "CampusOS API",
    "DESCRIPTION": "Education-to-Employment Operating System — Student Employability, Internships, Placements, Mentors, Outcomes",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth", "description": "Authentication"},
        {"name": "campus", "description": "Campus / Institution management"},
        {"name": "students", "description": "Student profiles and employability records"},
        {"name": "readiness", "description": "Career readiness and employability engine"},
        {"name": "internships", "description": "Internship, co-op, and apprenticeship management"},
        {"name": "placements", "description": "Campus placement drives and operations"},
        {"name": "employers", "description": "Employer CRM and partnership management"},
        {"name": "events", "description": "Campus events, fairs, and employer engagement"},
        {"name": "mentors", "description": "Alumni mentors and peer network"},
        {"name": "credentials", "description": "Credential wallet and digital badges"},
        {"name": "outcomes", "description": "Placement outcomes and analytics"},
        {"name": "advisors", "description": "Faculty and advisor workspace"},
        {"name": "assessments", "description": "Assessments, screening, and campus testing"},
        {"name": "trust", "description": "Trust, safety, and verification"},
        {"name": "integrations", "description": "Platform integrations (CareerOS, TalentOS, LMS, SIS)"},
        {"name": "billing", "description": "Billing, subscriptions, and payments"},
    ],
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Colombo"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ---------------------------------------------------------------------------
# Cache / Redis
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Storage — S3 or local
# ---------------------------------------------------------------------------

USE_S3 = os.getenv("USE_S3", "False") == "True"

if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1")
    AWS_DEFAULT_ACL = "private"
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@campusos.app")

# ---------------------------------------------------------------------------
# SMS / WhatsApp — Twilio
# ---------------------------------------------------------------------------

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")

# ---------------------------------------------------------------------------
# AI / OpenAI
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Elasticsearch
# ---------------------------------------------------------------------------

ELASTICSEARCH_DSL = {
    "default": {"hosts": os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")},
}

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Colombo"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.FileHandler",
            "filename": str(BASE_DIR / "logs" / "campusos.log"),
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# CampusOS-specific settings
# ---------------------------------------------------------------------------

CAMPUSOS_PLATFORM_NAME = "CampusOS"
CAMPUSOS_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
CAMPUSOS_API_URL = os.getenv("API_URL", "http://localhost:8000")

# Cross-platform bridge URLs
CAREEROS_API_URL = os.getenv("CAREEROS_API_URL", "")
CAREEROS_API_KEY = os.getenv("CAREEROS_API_KEY", "")
TALENTOS_API_URL = os.getenv("TALENTOS_API_URL", "")
TALENTOS_API_KEY = os.getenv("TALENTOS_API_KEY", "")
JOBFINDER_API_URL = os.getenv("JOBFINDER_API_URL", "")
JOBFINDER_API_KEY = os.getenv("JOBFINDER_API_KEY", "")
WORKFORCEOS_API_URL = os.getenv("WORKFORCEOS_API_URL", "")
WORKFORCEOS_API_KEY = os.getenv("WORKFORCEOS_API_KEY", "")

# Credential / badge provider
BADGR_API_KEY = os.getenv("BADGR_API_KEY", "")
BADGR_API_URL = os.getenv("BADGR_API_URL", "https://api.badgr.io/v2")

# File size limits
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
