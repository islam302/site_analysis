"""Development settings: convenient, verbose, insecure-by-design for local work."""
from decouple import Csv, config

from config.settings.base import *  # noqa: F401,F403
from config.settings.base import INSTALLED_APPS, LOGGING, MIDDLEWARE, REST_FRAMEWORK

DEBUG = True

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0",
    cast=Csv(),
)

# Browsable API is handy locally.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# Print emails to the console instead of sending them.
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Local-memory cache by default so dev needs no Redis. Set USE_REDIS_CACHE=True
# in .env to use the Redis backend from base settings instead.
if not config("USE_REDIS_CACHE", default=False, cast=bool):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "dev-cache",
        }
    }

# django-debug-toolbar (only if installed).
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar", "django_extensions"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Human-readable logs locally.
LOGGING["handlers"]["console"]["formatter"] = "verbose"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
