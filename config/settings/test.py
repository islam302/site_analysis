"""Test settings: fast, isolated, deterministic."""
from config.settings.base import *  # noqa: F401,F403
from config.settings.base import REST_FRAMEWORK

DEBUG = False

# Disable throttling in tests: the in-memory cache persists rate-limit counters
# across tests, which would otherwise produce spurious 429s. Rates are set to
# ``None`` (not removed) so explicit per-view throttle classes short-circuit to
# "allow" instead of raising ImproperlyConfigured on an unknown scope.
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "user": None,
    "anon": None,
    "auth": None,
    "analysis_burst": None,
    "analysis_daily": None,
}

# Fast password hashing for the test suite.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Run Celery tasks synchronously inside the calling process.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# In-memory email + cache so tests never touch external services.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Tests must never reach the real PageSpeed API; the client is mocked. A blank
# key would raise PageSpeedConfigError, so set a dummy value and patch requests.
GOOGLE_PAGESPEED_API_KEY = "test-pagespeed-key"
PAGESPEED_REQUEST_TIMEOUT = 5
