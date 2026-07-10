"""Celery task that produces a combined PDF report asynchronously.

The task runs the three tools concurrently (threads inside the worker), builds
the styled PDF, saves it to storage, and records the outcome on the job row.
Partial tool failures still produce a report; only an unexpected error marks the
whole job failed.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from celery import shared_task
from django.core.files.base import ContentFile

from apps.full_report.constants import FullReportStatus
from apps.full_report.models import FullReport
from apps.full_report.services import build_report_pdf, run_full_report

logger = logging.getLogger("apps.full_report")


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def run_full_report_task(self, report_id: str) -> str:
    """Generate the PDF for a FullReport job. Receives only a primitive id."""
    try:
        report = FullReport.objects.get(id=report_id)
    except FullReport.DoesNotExist:
        logger.warning("FullReport missing; skipping (%s)", report_id)
        return "missing"

    report.status = FullReportStatus.PROCESSING
    report.save(update_fields=["status", "updated_at"])
    logger.info("Full report processing", extra={"report_id": report_id, "url": report.url})

    try:
        result = run_full_report(url=report.url, strategy=report.strategy)
        pdf_bytes = build_report_pdf(result, lang=report.lang)

        host = (urlparse(report.url).hostname or "site").replace(".", "-")
        filename = f"analysis-{host}-{report.lang}.pdf"

        report.file.save(filename, ContentFile(pdf_bytes), save=False)
        report.tools_status = {
            "pagespeed": result["pagespeed"]["status"],
            "gtmetrix": result["gtmetrix"]["status"],
            "accessibility": result["accessibility"]["status"],
            "ssl": result["ssl"]["status"],
        }
        report.status = FullReportStatus.COMPLETED
        report.error_message = ""
        report.save()
    except Exception as exc:  # noqa: BLE001 - record failure, don't crash the worker
        report.status = FullReportStatus.FAILED
        report.error_message = str(exc)
        report.save(update_fields=["status", "error_message", "updated_at"])
        logger.error("Full report failed: %s (report %s)", exc, report_id)
        return "failed"

    logger.info("Full report completed", extra={"report_id": report_id})
    return report.status
