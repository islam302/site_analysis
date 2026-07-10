"""Business logic for GTmetrix analysis.

Mirrors the PageSpeed flow: ``submit_gtmetrix`` creates a pending report and
dispatches a Celery task; the worker calls ``process_gtmetrix`` which runs the
(async, polled) GTmetrix test and persists the parsed metrics.
"""
from __future__ import annotations

import logging
import uuid

from django.db import transaction

from apps.gtmetrix.constants import ReportStatus
from apps.gtmetrix.models import GTmetrixReport
from apps.gtmetrix.services.gtmetrix_client import poll_and_fetch, start_test

logger = logging.getLogger("apps.gtmetrix")


def _resolve_user(user):
    return user if getattr(user, "is_authenticated", False) else None


@transaction.atomic
def submit_gtmetrix(*, user, url: str) -> GTmetrixReport:
    """Create a pending GTmetrix report and dispatch the async task."""
    report = GTmetrixReport.objects.create(
        user=_resolve_user(user),
        url=url,
        status=ReportStatus.PENDING,
    )
    logger.info(
        "GTmetrix submitted",
        extra={"report_id": str(report.id), "url": url},
    )

    from apps.gtmetrix.tasks import run_gtmetrix_analysis

    transaction.on_commit(lambda: run_gtmetrix_analysis.delay(report_id=str(report.id)))
    return report


def process_gtmetrix(*, report_id: str | uuid.UUID) -> GTmetrixReport:
    """Run the GTmetrix test for a report and persist the results.

    Not wrapped in a single transaction so a persisted ``failed`` status
    survives the re-raise that drives Celery retries.
    """
    report = GTmetrixReport.objects.get(id=report_id)

    try:
        # Start the GTmetrix test only once and persist its id immediately. On a
        # retry (e.g. after a poll timeout) we resume polling the same test
        # instead of starting a new one — so a submission never spends more than
        # one GTmetrix credit.
        if not report.test_id:
            report.test_id = start_test(url=report.url)
            report.save(update_fields=["test_id", "updated_at"])
        result = poll_and_fetch(test_id=report.test_id)
    except Exception as exc:  # noqa: BLE001 - persist failure, then re-raise
        report.status = ReportStatus.FAILED
        report.error_message = str(exc)
        report.save(update_fields=["status", "error_message", "updated_at"])
        logger.warning(
            "GTmetrix failed: %s",
            str(exc),
            extra={"report_id": str(report.id)},
        )
        raise

    for field, value in result["metrics"].items():
        setattr(report, field, value)
    report.test_id = result["test_id"]
    report.raw_response = result["raw"]
    report.status = ReportStatus.COMPLETED
    report.error_message = ""
    report.save()

    logger.info("GTmetrix completed", extra={"report_id": str(report.id)})
    return report
