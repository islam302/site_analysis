"""Models for the broken-link checker."""
from django.db import models

from apps.common.models import BaseModel
from apps.common.validators import validate_http_url
from apps.linkchecker.constants import CrawlStatus, LinkType, StatusCategory


class CrawlJob(BaseModel):
    url = models.URLField(max_length=2048, db_index=True, validators=[validate_http_url])
    status = models.CharField(
        max_length=20,
        choices=CrawlStatus.choices,
        default=CrawlStatus.PENDING,
        db_index=True,
    )

    total_links_found = models.IntegerField(default=0)
    total_checked = models.IntegerField(default=0)
    total_healthy = models.IntegerField(default=0)
    total_broken = models.IntegerField(default=0)
    total_redirects = models.IntegerField(default=0)
    total_timeouts = models.IntegerField(default=0)

    crawl_depth = models.IntegerField(default=1)
    max_links = models.IntegerField(default=500)
    render_js = models.BooleanField(
        default=False,
        help_text="Render the page with a headless browser (for JS/SPA sites).",
    )
    duration_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "crawl job"
        verbose_name_plural = "crawl jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="crawl_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Crawl {self.url} [{self.status}]"


class LinkResult(BaseModel):
    crawl_job = models.ForeignKey(CrawlJob, on_delete=models.CASCADE, related_name="links")
    source_url = models.URLField(max_length=2048)
    target_url = models.URLField(max_length=2048, db_index=True)
    anchor_text = models.CharField(max_length=500, blank=True, default="")
    link_type = models.CharField(max_length=10, choices=LinkType.choices, db_index=True)

    http_status = models.IntegerField(null=True, blank=True)
    status_category = models.CharField(
        max_length=10, choices=StatusCategory.choices, db_index=True
    )
    response_time_ms = models.IntegerField(null=True, blank=True)
    redirect_url = models.URLField(max_length=2048, blank=True, default="")
    error_detail = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        verbose_name = "link result"
        verbose_name_plural = "link results"
        ordering = ["status_category", "target_url"]
        indexes = [
            models.Index(fields=["crawl_job", "status_category"], name="link_job_category_idx"),
            models.Index(fields=["crawl_job", "link_type"], name="link_job_type_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.status_category}] {self.target_url}"
