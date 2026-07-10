"""Business logic for PageSpeed analysis.

Flow (see async_processing_flow.svg):
1. ``submit_analysis`` validates input, creates a pending report, dispatches a
   Celery task, and returns immediately (HTTP 202).
2. The worker calls ``process_analysis``, which hits the PageSpeed API, parses
   the result, updates the report, upserts the per-URL history rollup, and
   invalidates the cached history.
3. ``compare_urls`` submits two analyses side by side.
"""
from __future__ import annotations

import logging
import uuid

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.analysis.constants import ReportStatus
from apps.analysis.models import AnalysisHistory, AnalysisReport
from apps.analysis.selectors import invalidate_history_cache
from apps.analysis.services.pagespeed_client import fetch_pagespeed, parse_pagespeed

logger = logging.getLogger("apps.analysis")


def _resolve_user(user):
    """Return a persisted User or None for anonymous/unauthenticated callers."""
    return user if getattr(user, "is_authenticated", False) else None


@transaction.atomic
def submit_analysis(*, user, url: str, strategy: str) -> AnalysisReport:
    """Create a pending report and dispatch the async PageSpeed task.

    ``user`` may be an ``AnonymousUser`` (anonymous submissions) — it is stored
    as ``None`` and such reports are not tracked in per-user history.
    """
    user = _resolve_user(user)
    report = AnalysisReport.objects.create(
        user=user,
        url=url,
        strategy=strategy,
        status=ReportStatus.PENDING,
    )
    logger.info(
        "Analysis submitted",
        extra={
            "report_id": str(report.id),
            "user_id": str(user.id) if user else None,
            "url": url,
        },
    )

    # Import inside the function to avoid a circular import (tasks import services).
    from apps.analysis.tasks import run_pagespeed_analysis

    transaction.on_commit(lambda: run_pagespeed_analysis.delay(report_id=str(report.id)))
    return report


@transaction.atomic
def _upsert_history(*, user, url: str) -> None:
    """Increment the per-URL analysis counter and refresh its timestamp."""
    now = timezone.now()
    obj, created = AnalysisHistory.objects.get_or_create(
        user=user,
        url=url,
        defaults={"reports_count": 1, "last_analyzed_at": now},
    )
    if not created:
        AnalysisHistory.objects.filter(pk=obj.pk).update(
            reports_count=F("reports_count") + 1,
            last_analyzed_at=now,
            updated_at=now,
        )
    invalidate_history_cache(user_id=user.id)


def process_analysis(*, report_id: str | uuid.UUID) -> AnalysisReport:
    """Run the PageSpeed analysis for a report and persist the results.

    Idempotent and safe to retry. The external API call is made *without*
    holding a DB lock. On failure the report is marked ``failed`` in its own
    committed write and the exception is re-raised so Celery can apply its
    retry policy. Not wrapped in a single ``atomic`` block precisely so the
    failure status survives the re-raise.
    """
    report = AnalysisReport.objects.get(id=report_id)

    try:
        raw = fetch_pagespeed(url=report.url, strategy=report.strategy)
    except Exception as exc:  # noqa: BLE001 - persist failure, then re-raise
        report.status = ReportStatus.FAILED
        report.error_message = str(exc)
        report.save(update_fields=["status", "error_message", "updated_at"])
        logger.warning("Analysis failed: %s (report %s)", str(exc), str(report.id))
        raise

    metrics = parse_pagespeed(raw)
    for field, value in metrics.items():
        setattr(report, field, value)
    report.raw_response = raw
    report.status = ReportStatus.COMPLETED
    report.error_message = ""
    report.save()

    # Per-user history rollup only applies to authenticated submissions.
    if report.user_id is not None:
        _upsert_history(user=report.user, url=report.url)
    logger.info("Analysis completed", extra={"report_id": str(report.id)})
    return report
