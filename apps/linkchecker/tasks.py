"""Celery task that runs a full link check for a CrawlJob.

Fetches the page, extracts links, checks each concurrently with a thread pool,
bulk-inserts the results, and rolls up the per-category counts on the job.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from celery import shared_task
from django.conf import settings

from apps.linkchecker.constants import PROGRESS_EVERY, CrawlStatus, StatusCategory
from apps.linkchecker.exceptions import RobotsDisallowedError
from apps.linkchecker.models import CrawlJob, LinkResult
from apps.linkchecker.services import (
    check_single_link,
    extract_links,
    fetch_page_html,
    is_allowed_by_robots,
    render_page_html,
)

logger = logging.getLogger("apps.linkchecker")


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def run_link_check(self, job_id: str) -> str:
    """Process a CrawlJob end to end. Receives only a primitive id."""
    try:
        job = CrawlJob.objects.get(id=job_id)
    except CrawlJob.DoesNotExist:
        logger.warning("CrawlJob missing; skipping (%s)", job_id)
        return "missing"

    started = time.monotonic()
    job.status = CrawlStatus.CRAWLING
    job.save(update_fields=["status", "updated_at"])
    logger.info("Crawl started", extra={"job_id": job_id, "url": job.url})

    try:
        if not is_allowed_by_robots(url=job.url):
            raise RobotsDisallowedError()

        # Render with a headless browser for JS/SPA sites; fast httpx otherwise.
        html = render_page_html(url=job.url) if job.render_js else fetch_page_html(url=job.url)
        links = extract_links(html_content=html, base_url=job.url)[: job.max_links]

        job.total_links_found = len(links)
        job.status = CrawlStatus.CHECKING_LINKS
        job.save(update_fields=["total_links_found", "status", "updated_at"])

        results: list[LinkResult] = []
        checked = 0
        with ThreadPoolExecutor(max_workers=settings.LINKCHECKER_MAX_WORKERS) as pool:
            futures = {
                pool.submit(check_single_link, url=link["target_url"]): link
                for link in links
            }
            for future in as_completed(futures):
                link = futures[future]
                outcome = future.result()
                results.append(
                    LinkResult(
                        crawl_job=job,
                        source_url=link["source_url"],
                        target_url=link["target_url"],
                        anchor_text=link["anchor_text"],
                        link_type=link["link_type"],
                        **outcome,
                    )
                )
                checked += 1
                if checked % PROGRESS_EVERY == 0:
                    CrawlJob.objects.filter(id=job.id).update(total_checked=checked)

        LinkResult.objects.bulk_create(results, batch_size=500)

        def _count(category: str) -> int:
            return sum(1 for r in results if r.status_category == category)

        job.total_checked = len(results)
        job.total_healthy = _count(StatusCategory.HEALTHY)
        job.total_broken = _count(StatusCategory.BROKEN)
        job.total_redirects = _count(StatusCategory.REDIRECT)
        job.total_timeouts = _count(StatusCategory.TIMEOUT)
        job.duration_seconds = round(time.monotonic() - started, 2)
        job.status = CrawlStatus.COMPLETED
        job.error_message = ""
        job.save()
    except Exception as exc:  # noqa: BLE001 - record failure on the job
        job.status = CrawlStatus.FAILED
        job.error_message = str(exc)
        job.duration_seconds = round(time.monotonic() - started, 2)
        job.save(update_fields=["status", "error_message", "duration_seconds", "updated_at"])
        logger.warning("Crawl failed: %s (job %s)", exc, job_id)
        return "failed"

    logger.info(
        "Crawl completed",
        extra={"job_id": job_id, "broken": job.total_broken, "checked": job.total_checked},
    )
    return job.status
