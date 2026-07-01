"""Celery tasks for the analysis app.

The task is a thin, idempotent wrapper that delegates the real work to
``process_analysis`` in the service layer. It retries on transient network
errors with exponential backoff.
"""
from __future__ import annotations

import logging

import requests
from celery import shared_task

from apps.analysis.exceptions import PageSpeedAPIError
from apps.analysis.models import AnalysisReport
from apps.analysis.services import process_analysis

logger = logging.getLogger("apps.analysis")


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(requests.ConnectionError, requests.Timeout, PageSpeedAPIError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def run_pagespeed_analysis(self, report_id: str) -> str:
    """Process a pending analysis report via the PageSpeed Insights API.

    Returns the final report status. Receives only a primitive ``report_id``.
    """
    logger.info(
        "run_pagespeed_analysis started",
        extra={"report_id": report_id, "attempt": self.request.retries + 1},
    )
    try:
        report = process_analysis(report_id=report_id)
    except AnalysisReport.DoesNotExist:
        logger.warning("Report missing; skipping", extra={"report_id": report_id})
        return "missing"

    logger.info(
        "run_pagespeed_analysis finished",
        extra={"report_id": report_id, "status": report.status},
    )
    return report.status
