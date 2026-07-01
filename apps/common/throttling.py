"""Custom throttle classes shared across apps.

The ``auth`` scope is applied explicitly on sensitive auth endpoints (login,
register, password reset) to rate-limit credential abuse independently of the
global user/anon throttles.
"""
from rest_framework.throttling import SimpleRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    """Throttle keyed on client IP for unauthenticated auth endpoints.

    Rate is configured via ``DEFAULT_THROTTLE_RATES['auth']`` (5/min).
    """

    scope = "auth"

    def get_cache_key(self, request, view) -> str | None:
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
