"""Celery task for GTmetrix analysis.

Retry policy (explicit, so it always stops):
- Transient errors (network / 5xx / timeout) -> retry up to ``MAX_RETRIES`` (3)
  with exponential backoff, then give up and mark the report failed.
- Client errors (4xx, e.g. out of credits / bad URL) -> stop immediately;
  retrying cannot fix them.
Every attempt and outcome is logged with the real error message.
"""
from __future__ import annotations

import logging

import requests
from celery import shared_task

from apps.gtmetrix.exceptions import (
    GTmetrixAPIError,
    GTmetrixClientError,
    GTmetrixTimeoutError,
)
from apps.gtmetrix.models import GTmetrixReport
from apps.gtmetrix.services import process_gtmetrix

logger = logging.getLogger("apps.gtmetrix")

MAX_RETRIES = 3
# Transient failures worth retrying. Client (4xx) errors are fatal → no retry.
RETRYABLE_ERRORS = (
    requests.ConnectionError,
    requests.Timeout,
    GTmetrixAPIError,
    GTmetrixTimeoutError,
)


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=MAX_RETRIES,
)
def run_gtmetrix_analysis(self, report_id: str) -> str:
    """Process a pending GTmetrix report. Receives only a primitive id."""
    attempt = self.request.retries + 1
    logger.info(
        "GTmetrix task attempt %s/%s (report %s)",
        attempt,
        MAX_RETRIES + 1,
        report_id,
    )

    try:
        report = process_gtmetrix(report_id=report_id)

    except GTmetrixReport.DoesNotExist:
        logger.warning("GTmetrix report missing; skipping (report %s)", report_id)
        return "missing"

    except GTmetrixClientError as exc:
        # Out of credits / bad request / etc. — retrying will just fail again.
        logger.error("GTmetrix task STOPPED (client error): %s (report %s)", exc, report_id)
        return "failed"

    except RETRYABLE_ERRORS as exc:
        if self.request.retries >= MAX_RETRIES:
            logger.error(
                "GTmetrix task GAVE UP after %s attempts: %s (report %s)",
                attempt,
                exc,
                report_id,
            )
            return "failed"
        countdown = min(5 * 2**self.request.retries, 60)
        logger.warning(
            "GTmetrix task retry %s/%s in %ss after error: %s (report %s)",
            attempt,
            MAX_RETRIES,
            countdown,
            exc,
            report_id,
        )
        raise self.retry(exc=exc, countdown=countdown)

    logger.info("GTmetrix task finished: %s (report %s)", report.status, report_id)
    return report.status
