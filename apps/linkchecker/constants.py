"""Constants for the link checker."""
from django.db import models


class CrawlStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CRAWLING = "crawling", "Crawling"
    CHECKING_LINKS = "checking_links", "Checking links"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class LinkType(models.TextChoices):
    INTERNAL = "internal", "Internal"
    EXTERNAL = "external", "External"


class StatusCategory(models.TextChoices):
    HEALTHY = "healthy", "Healthy"
    BROKEN = "broken", "Broken"
    REDIRECT = "redirect", "Redirect"
    TIMEOUT = "timeout", "Timeout"
    ERROR = "error", "Error"


# HTML tag -> attribute that holds a URL.
LINK_SOURCES = (
    ("a", "href"),
    ("img", "src"),
    ("script", "src"),
    ("link", "href"),
)

MAX_REDIRECTS = 10
PROGRESS_EVERY = 50
