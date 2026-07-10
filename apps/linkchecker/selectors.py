"""Read-only queries for the link checker."""
from __future__ import annotations

import uuid

from django.db.models import QuerySet

from apps.linkchecker.exceptions import CrawlJobNotFoundError
from apps.linkchecker.models import CrawlJob, LinkResult


def get_crawl_jobs() -> QuerySet[CrawlJob]:
    """Return all crawl jobs, newest first."""
    return CrawlJob.objects.all().order_by("-created_at")


def get_crawl_detail(*, job_id: uuid.UUID | str) -> CrawlJob:
    """Return one crawl job or raise :class:`CrawlJobNotFoundError`."""
    try:
        return CrawlJob.objects.get(id=job_id)
    except (CrawlJob.DoesNotExist, ValueError, TypeError):
        raise CrawlJobNotFoundError(extra={"job_id": str(job_id)})


def get_link_results(*, job_id: uuid.UUID | str) -> QuerySet[LinkResult]:
    """Return the link results for a job (existence validated first)."""
    get_crawl_detail(job_id=job_id)
    return LinkResult.objects.filter(crawl_job_id=job_id).order_by("status_category", "target_url")
