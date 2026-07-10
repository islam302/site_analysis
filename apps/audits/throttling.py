"""Per-user throttle for audit submissions (10/min)."""
from rest_framework.throttling import UserRateThrottle


class AuditRateThrottle(UserRateThrottle):
    scope = "audit"
