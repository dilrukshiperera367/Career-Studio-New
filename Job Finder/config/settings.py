"""
ConnectOS Job Finder — Django Settings
"""
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Core ───────────────────────────────────────────────────────────────────
_secret_key = os.environ.get("SECRET_KEY", "")
if not _secret_key:
    if os.environ.get("DEBUG", "true").lower() == "true":
        import secrets as _secrets
        _secret_key = "django-insecure-dev-" + _secrets.token_hex(32)
    else:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Set it to a long random string before deploying."
        )
SECRET_KEY = _secret_key

DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

USE_SQLITE = os.environ.get("USE_SQLITE", "true").lower() == "true"

# ── Applications ───────────────────────────────────────────────────────────
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
    "corsheaders",
    "django_filters",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.shared",
    "apps.accounts",
    "apps.taxonomy",
    "apps.candidates",
    "apps.employers",
    "apps.jobs",
    "apps.applications",
    "apps.search",
    "apps.ats_connector",
    "apps.payments",
    "apps.messaging",
    "apps.notifications",
    "apps.reviews",
    "apps.content",
    "apps.assessments",
    "apps.foreign_employment",
    "apps.moderation",
    "apps.analytics",
    "apps.admin_panel",
    "apps.ai_tools",
    "apps.governance",
    # ── Shared Foundation ──
    "apps.engine.workflows",
    "apps.engine.communications",
    "apps.trust.verification",
    # ── Core ──
    "apps.core.credentials",
    "apps.consent",
    # ── New Marketplace Apps ──
    "apps.marketplace_search",
    "apps.seo_indexing",
    "apps.job_quality",
    "apps.marketplace_billing",
    "apps.company_intelligence",
    "apps.salary_intelligence",
    "apps.promotions_ads",
    "apps.trust_ops",
    "apps.retention_growth",
    "apps.mobile_api",
    "apps.marketplace_analytics",
    "apps.feed_normalization",
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

# ── Middleware ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.shared.middleware.RequestLanguageMiddleware",
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
ASGI_APPLICATION = "config.asgi.application"

# ── Database ───────────────────────────────────────────────────────────────
if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "jobfinder_db"),
            "USER": os.environ.get("DB_USER", "jobfinder_user"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "jobfinder_password"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

# ── Auth ───────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ──────────────────────────────────────────────────
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("si", "සිංහල"),
    ("ta", "தமிழ்"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_L10N = True
TIME_ZONE = "Asia/Colombo"
USE_TZ = True

# ── Static & Media ─────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── DRF ────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.shared.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "login": "5/minute",
    },
    "EXCEPTION_HANDLER": "apps.shared.exceptions.custom_exception_handler",
}

# ── Platform identity ────────────────────────────────────────────────────────
PLATFORM_PORTAL_NAME = "jobfinder"
JOBFINDER_BASE_URL = os.environ.get("JOBFINDER_BASE_URL", "http://localhost:3001")

# ── JWT ────────────────────────────────────────────────────────────────────
_jwt_signing_key = os.environ.get("SHARED_JWT_SECRET", "")
if not _jwt_signing_key:
    if not DEBUG:
        raise RuntimeError(
            "SHARED_JWT_SECRET environment variable must be set in production."
        )
    _jwt_signing_key = SECRET_KEY

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": _jwt_signing_key,
    # Keep portal-specific serializer — it already embeds tenant/role claims;
    # platform_auth.PlatformTokenObtainSerializer is its base class equivalent.
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CustomTokenObtainPairSerializer",
}

# ── CORS ───────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3001,http://localhost:3000"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# ── Celery ─────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/4")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/5")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Colombo"
# CELERY_TASK_ALWAYS_EAGER must remain False in production to avoid blocking
# the request cycle with background tasks.
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"

# ── ConnectOS platform event handlers ───────────────────────────────────
PLATFORM_EVENT_HANDLERS = {
    "job.posted":  "apps.jobs.event_handlers.on_job_posted",
    "job.updated": "apps.jobs.event_handlers.on_job_updated",
    "job.closed":  "apps.jobs.event_handlers.on_job_closed",
}

# ── Cache ──────────────────────────────────────────────────────────────────
if USE_SQLITE:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/6"),
        }
    }

# ── File Storage ───────────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_RESUME_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# ── ATS Integration ───────────────────────────────────────────────────────
ATS_BASE_URL = os.environ.get("ATS_BASE_URL", "http://localhost:8000")
ATS_WEBHOOK_SECRET = os.environ.get("ATS_WEBHOOK_SECRET", "dev-webhook-secret")

# ── OAuth (Social Auth) ───────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "")
LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")

# ── Email ──────────────────────────────────────────────────────────────────
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@findjobs.lk")

# ── Security ──────────────────────────────────────────────────────────────
# Cookie security (applies in all environments)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # Must be readable by JS for CSRF token injection
CSRF_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() == "true"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ── Logging ────────────────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "jobfinder.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING"},
        "apps": {"handlers": ["console", "file"], "level": "DEBUG" if DEBUG else "INFO"},
    },
}
