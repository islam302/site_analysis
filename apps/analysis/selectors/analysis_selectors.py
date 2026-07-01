"""Read-only queries for analysis reports and history.

Selectors never mutate data. ``get_analysis_history`` is cached per user for
5 minutes; services call :func:`invalidate_history_cache` after writes.
"""
from __future__ import annotations

import uuid

from django.core.cache import cache
from django.db.models import QuerySet

from apps.analysis.constants import HISTORY_CACHE_KEY, HISTORY_CACHE_TIMEOUT
from apps.analysis.exceptions import ReportNotFoundError
from apps.analysis.models import AnalysisHistory, AnalysisReport


def get_user_reports(*, user, filters: dict | None = None) -> QuerySet[AnalysisReport]:
    """Return the user's reports, optionally narrowed by a ``filters`` mapping.

    The view applies its ``FilterSet`` via the filter backend; the optional
    ``filters`` argument lets services/tests reuse the same base query with
    simple equality filters (e.g. ``{"strategy": "mobile"}``).
    """
    qs = AnalysisReport.objects.filter(user=user).order_by("-created_at")
    if filters:
        allowed = {"url", "strategy", "status"}
        clean = {k: v for k, v in filters.items() if k in allowed and v is not None}
        if clean:
            qs = qs.filter(**clean)
    return qs


def get_report_detail(*, user, report_id: uuid.UUID | str) -> AnalysisReport:
    """Return a single report owned by ``user`` or raise ReportNotFoundError."""
    try:
        return AnalysisReport.objects.select_related("user").get(user=user, id=report_id)
    except (AnalysisReport.DoesNotExist, ValueError, TypeError):
        raise ReportNotFoundError(extra={"report_id": str(report_id)})


def _history_cache_key(user_id) -> str:
    return HISTORY_CACHE_KEY.format(user_id=user_id)


def get_analysis_history(*, user) -> list[AnalysisHistory]:
    """Return the user's analysis history (unique URLs + counts), cached 5 min.

    Returns a materialized list (not a lazy queryset) so the value can be cached
    and paginated safely.
    """
    key = _history_cache_key(user.id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    history = list(
        AnalysisHistory.objects.filter(user=user).order_by("-last_analyzed_at")
    )
    cache.set(key, history, HISTORY_CACHE_TIMEOUT)
    return history


def invalidate_history_cache(*, user_id) -> None:
    """Drop the cached history for a user (call after history writes)."""
    cache.delete(_history_cache_key(user_id))
