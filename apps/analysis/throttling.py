"""Per-user throttles for analysis submission endpoints.

Two scopes apply simultaneously to ``analyze`` / ``compare``:
- ``analysis_burst``  -> 5 requests/minute  per user
- ``analysis_daily``  -> 100 requests/day    per user

Both are keyed on the authenticated user id so limits are per-account.
"""
from rest_framework.throttling import UserRateThrottle


class AnalysisBurstThrottle(UserRateThrottle):
    scope = "analysis_burst"


class AnalysisDailyThrottle(UserRateThrottle):
    scope = "analysis_daily"
