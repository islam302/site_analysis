"""Enumerations and tunables for the PageSpeed analysis domain."""
from django.db import models


class Strategy(models.TextChoices):
    MOBILE = "mobile", "Mobile"
    DESKTOP = "desktop", "Desktop"


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


# Lighthouse category keys requested from the PageSpeed Insights API and the
# model field each maps to.
PAGESPEED_CATEGORIES = ("performance", "accessibility", "best-practices", "seo")

CATEGORY_TO_FIELD = {
    "performance": "performance_score",
    "accessibility": "accessibility_score",
    "best-practices": "best_practices_score",
    "seo": "seo_score",
}

# Lighthouse audit id -> (model field, unit conversion applied during parsing).
# ``numericValue`` is in milliseconds for timing audits and unitless for CLS.
AUDIT_TO_FIELD = {
    "first-contentful-paint": ("first_contentful_paint", "ms_to_s"),
    "largest-contentful-paint": ("largest_contentful_paint", "ms_to_s"),
    "total-blocking-time": ("total_blocking_time", "ms"),
    "cumulative-layout-shift": ("cumulative_layout_shift", "raw"),
    "speed-index": ("speed_index", "ms_to_s"),
    "interactive": ("time_to_interactive", "ms_to_s"),
}

# Cache configuration for analysis history.
HISTORY_CACHE_KEY = "analysis:history:{user_id}"
HISTORY_CACHE_TIMEOUT = 60 * 5  # 5 minutes
