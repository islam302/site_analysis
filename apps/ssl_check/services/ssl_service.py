"""Business logic for SSL/TLS checks.

``submit_ssl_check`` creates a pending report and dispatches a Celery task;
the worker calls ``process_ssl_check`` which runs the (synchronous, but slow-ish)
sslyze scan and persists the result.
"""
from __future__ import annotations

import logging
import uuid
from urllib.parse import urlparse

from django.db import transaction

from apps.ssl_check.constants import ReportStatus
from apps.ssl_check.models import SSLReport
from apps.ssl_check.services.sslyze_scanner import run_ssl_scan

logger = logging.getLogger("apps.ssl_check")


def _resolve_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _host_from_url(url: str) -> str:
    return urlparse(url).hostname or url


@transaction.atomic
def submit_ssl_check(*, user, url: str) -> SSLReport:
    """Create a pending SSL report and dispatch the async scan task."""
    report = SSLReport.objects.create(
        user=_resolve_user(user),
        url=url,
        host=_host_from_url(url),
        status=ReportStatus.PENDING,
    )
    logger.info("SSL check submitted", extra={"report_id": str(report.id), "host": report.host})

    from apps.ssl_check.tasks import run_ssl_scan_task

    transaction.on_commit(lambda: run_ssl_scan_task.delay(report_id=str(report.id)))
    return report


def process_ssl_check(*, report_id: str | uuid.UUID) -> SSLReport:
    """Run the sslyze scan for a report and persist the result.

    On failure the report is marked ``failed`` (in its own committed write) and
    the exception is re-raised so Celery can apply its retry policy.
    """
    report = SSLReport.objects.get(id=report_id)

    try:
        result = run_ssl_scan(host=report.host)
    except Exception as exc:  # noqa: BLE001 - persist failure, then re-raise
        report.status = ReportStatus.FAILED
        report.error_message = str(exc)
        report.save(update_fields=["status", "error_message", "updated_at"])
        logger.warning("SSL scan failed: %s (report %s)", exc, str(report.id))
        raise

    for field, value in result.items():
        setattr(report, field, value)
    report.status = ReportStatus.COMPLETED
    report.error_message = ""
    report.save()
    logger.info("SSL check completed", extra={"report_id": str(report.id), "grade": report.grade})
    return report
