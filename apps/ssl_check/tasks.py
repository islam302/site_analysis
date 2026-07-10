"""Celery task for SSL/TLS scans.

The sslyze scan is synchronous but can take ~10-30s, so it runs on a worker to
keep the request non-blocking. Transient failures retry up to ``MAX_RETRIES``
then stop.
"""
from __future__ import annotations

import logging

from celery import shared_task

from apps.ssl_check.exceptions import SSLScanError
from apps.ssl_check.models import SSLReport
from apps.ssl_check.services import process_ssl_check

logger = logging.getLogger("apps.ssl_check")

MAX_RETRIES = 3


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True, max_retries=MAX_RETRIES)
def run_ssl_scan_task(self, report_id: str) -> str:
    """Process a pending SSL report. Receives only a primitive id."""
    attempt = self.request.retries + 1
    logger.info("SSL task attempt %s/%s (report %s)", attempt, MAX_RETRIES + 1, report_id)

    try:
        report = process_ssl_check(report_id=report_id)
    except SSLReport.DoesNotExist:
        logger.warning("SSL report missing; skipping (%s)", report_id)
        return "missing"
    except SSLScanError as exc:
        if self.request.retries >= MAX_RETRIES:
            logger.error("SSL task GAVE UP after %s attempts: %s (report %s)", attempt, exc, report_id)
            return "failed"
        countdown = min(5 * 2**self.request.retries, 60)
        logger.warning("SSL task retry %s/%s in %ss: %s", attempt, MAX_RETRIES, countdown, exc)
        raise self.retry(exc=exc, countdown=countdown)

    logger.info("SSL task finished: %s (report %s)", report.status, report_id)
    return report.status
