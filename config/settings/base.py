"""Shared settings for all environments.

Environment-specific modules (``development``, ``production``, ``test``) import
everything from here and override what they need. All configurable values are
read from the environment via :mod:`python-decouple`.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

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
]

LOCAL_APPS = [
    "apps.common",
    "apps.users",
    "apps.analysis",
    "apps.gtmetrix",
    "apps.speed_test",
    "apps.credits",
    "apps.audits",
    "apps.ssl_check",
    "apps.linkchecker",
    "apps.full_report",
    "apps.validator",
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
    "apps.common.middleware.CorrelationIdMiddleware",
    "apps.common.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
        "CONN_HEALTH_CHECKS": True,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.users.validators.PasswordComplexityValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# ---------------------------------------------------------------------------
# REST framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "apps.users.authentication.ApiKeyAuthentication",
    ),
    # Public by default; identity-scoped endpoints (me, api-key, admin, etc.)
    # opt back into IsAuthenticated explicitly on their views.
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
    # Free up ``?format=`` as a query filter (validator filters schemas by
    # ``format``); DRF's content-negotiation override moves to ``response_format``.
    "URL_FORMAT_OVERRIDE": "response_format",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "100/day",
        "auth": "5/min",
        # Analysis submission limits (applied per authenticated user).
        "analysis_burst": "5/min",
        "analysis_daily": "100/day",
        # Accessibility audit submissions (per authenticated user).
        "audit": "10/min",
        # Link-checker crawl submissions (per client IP).
        "crawl_burst": "3/min",
        "crawl_daily": "20/day",
        # Structured-data validation submissions (per authenticated user).
        "validator_burst": "10/min",
        "validator_daily": "200/day",
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Site Analysis API",
    "DESCRIPTION": (
        "Multi-tool website analysis platform: Google PageSpeed, GTmetrix, a "
        "combined speed test, and WAVE accessibility audits — with JWT + API-key "
        "auth and a credit/quota system."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]+",
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
    # Disambiguate the several ``status`` enums (tools share pending/completed/
    # failed; the full report adds "processing").
    "ENUM_NAME_OVERRIDES": {
        "ReportStatusEnum": "apps.analysis.constants.ReportStatus.choices",
        "FullReportStatusEnum": "apps.full_report.constants.FullReportStatus.choices",
        "CrawlStatusEnum": "apps.linkchecker.constants.CrawlStatus.choices",
        # NB: ValidationStatus has the same choice set as FullReportStatus, so it
        # reuses FullReportStatusEnum — a separate override would be a duplicate.
    },
}

# ---------------------------------------------------------------------------
# Caching (Redis)
# ---------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "siteanalysis",
    }
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
# When True, tasks run inline in the calling process (no broker/worker needed).
# Handy for local testing: set CELERY_TASK_ALWAYS_EAGER=True in .env.
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = config("CELERY_TASK_EAGER_PROPAGATES", default=False, cast=bool)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TRACK_STARTED = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=25, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@siteanalysis.local")

FRONTEND_BASE_URL = config("FRONTEND_BASE_URL", default="http://localhost:3000")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Google PageSpeed Insights
# ---------------------------------------------------------------------------
GOOGLE_PAGESPEED_API_KEY = config("GOOGLE_PAGESPEED_API_KEY", default="")
PAGESPEED_REQUEST_TIMEOUT = config("PAGESPEED_REQUEST_TIMEOUT", default=60, cast=int)

# ---------------------------------------------------------------------------
# SSL/TLS scanning (sslyze — local scanner, no external API or key)
# ---------------------------------------------------------------------------
SSL_SCAN_TIMEOUT = config("SSL_SCAN_TIMEOUT", default=30, cast=int)

# ---------------------------------------------------------------------------
# Link checker (httpx + BeautifulSoup, no external API)
# ---------------------------------------------------------------------------
# A browser-like UA by default — many sites serve a stripped/blocked page to
# obvious bots. Override with LINKCHECKER_USER_AGENT if you want to identify the bot.
LINKCHECKER_USER_AGENT = config(
    "LINKCHECKER_USER_AGENT",
    default=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
)
LINKCHECKER_TIMEOUT = config("LINKCHECKER_TIMEOUT", default=10, cast=int)
# Extra time for JS rendering (Playwright), seconds.
LINKCHECKER_RENDER_TIMEOUT = config("LINKCHECKER_RENDER_TIMEOUT", default=30, cast=int)
LINKCHECKER_MAX_WORKERS = config("LINKCHECKER_MAX_WORKERS", default=20, cast=int)
LINKCHECKER_MAX_LINKS = config("LINKCHECKER_MAX_LINKS", default=500, cast=int)
# Verify TLS certs while crawling. Set False behind a TLS-intercepting proxy or
# to reach sites with broken chains (the crawler checks reachability, not trust).
LINKCHECKER_VERIFY_SSL = config("LINKCHECKER_VERIFY_SSL", default=True, cast=bool)

# ---------------------------------------------------------------------------
# WAVE accessibility API (WebAIM)
# ---------------------------------------------------------------------------
WAVE_API_KEY = config("WAVE_API_KEY", default="")
WAVE_BASE_URL = config("WAVE_BASE_URL", default="https://wave.webaim.org/api/request")
WAVE_REPORT_TYPE = config("WAVE_REPORT_TYPE", default=2, cast=int)
WAVE_REQUEST_TIMEOUT = config("WAVE_REQUEST_TIMEOUT", default=60, cast=int)

# ---------------------------------------------------------------------------
# GTmetrix (API 2.0)
# ---------------------------------------------------------------------------
GTMETRIX_API_KEY = config("GTMETRIX_API_KEY", default="")
GTMETRIX_BASE_URL = config("GTMETRIX_BASE_URL", default="https://gtmetrix.com/api/2.0/")
GTMETRIX_REQUEST_TIMEOUT = config("GTMETRIX_REQUEST_TIMEOUT", default=30, cast=int)
# Polling for an async GTmetrix test to finish.
GTMETRIX_POLL_INTERVAL = config("GTMETRIX_POLL_INTERVAL", default=5, cast=int)
GTMETRIX_POLL_MAX_SECONDS = config("GTMETRIX_POLL_MAX_SECONDS", default=300, cast=int)

# ---------------------------------------------------------------------------
# Full report — which tools to run
# ---------------------------------------------------------------------------
# Comma-separated list of the tools the combined full report should run. Any
# tool omitted here is skipped (marked "not included" in the PDF and reported as
# "skipped" in tools_status). Valid keys:
#   pagespeed, gtmetrix, accessibility, ssl, links, structured_data
# Example (turn GTmetrix off when out of credits):
#   FULL_REPORT_TOOLS=pagespeed,accessibility,ssl,links,structured_data
FULL_REPORT_TOOLS = config(
    "FULL_REPORT_TOOLS",
    default="pagespeed,gtmetrix,accessibility,ssl,links,structured_data",
    cast=Csv(),
)

# Tokens for email verification & password reset (seconds).
EMAIL_VERIFICATION_TIMEOUT = 60 * 60 * 24  # 24 hours
PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hour

# ---------------------------------------------------------------------------
# PDF reports — Arabic-capable TTF font (needed to render the ``ar`` version).
# ---------------------------------------------------------------------------
PDF_ARABIC_FONT = config("PDF_ARABIC_FONT", default=r"C:\Windows\Fonts\arial.ttf")
PDF_ARABIC_FONT_BOLD = config("PDF_ARABIC_FONT_BOLD", default=r"C:\Windows\Fonts\arialbd.ttf")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        },
        "verbose": {
            "format": "[{asctime}] {levelname} {name}:{lineno} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
