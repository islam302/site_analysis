"""Per-user throttles for validation submissions (10/min, 200/day)."""
from rest_framework.throttling import UserRateThrottle


class ValidationBurstThrottle(UserRateThrottle):
    scope = "validator_burst"


class ValidationDailyThrottle(UserRateThrottle):
    scope = "validator_daily"
