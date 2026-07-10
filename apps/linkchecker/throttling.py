"""Per-IP throttles for crawl submissions."""
from rest_framework.throttling import SimpleRateThrottle


class _IPThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view) -> str | None:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class CrawlBurstThrottle(_IPThrottle):
    scope = "crawl_burst"


class CrawlDailyThrottle(_IPThrottle):
    scope = "crawl_daily"
