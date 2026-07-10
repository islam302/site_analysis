"""Client for the WAVE accessibility API (https://wave.webaim.org/api/request).

WAVE is synchronous: one GET returns the full accessibility report. This module
performs the HTTP request and flattens the response into our schema; the service
layer persists the result. Note WAVE returns HTTP 200 even for logical failures,
signalling them via ``status.success == false``.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

from apps.audits.constants import WAVE_CATEGORY_MAP
from apps.audits.exceptions import WaveAPIError, WaveConfigError

logger = logging.getLogger("apps.audits")


def fetch_wave(*, url: str, reporttype: int | None = None) -> dict:
    """Call the WAVE API for ``url`` and return the raw JSON response.

    Raises:
        WaveConfigError: no API key configured.
        WaveAPIError: network error, non-2xx, bad JSON, or ``status.success`` false.
    """
    api_key = settings.WAVE_API_KEY
    if not api_key:
        raise WaveConfigError()

    params = {
        "key": api_key,
        "url": url,
        "reporttype": reporttype or settings.WAVE_REPORT_TYPE,
    }
    try:
        response = requests.get(
            settings.WAVE_BASE_URL, params=params, timeout=settings.WAVE_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        logger.warning("WAVE HTTP error %s for %s", code, url)
        raise WaveAPIError(f"WAVE returned HTTP {code}.", extra={"status_code": code})
    except (requests.RequestException, ValueError) as exc:
        logger.warning("WAVE request failed for %s: %s", url, exc)
        raise WaveAPIError(extra={"error": str(exc)})

    if not data.get("status", {}).get("success", False):
        reason = data.get("status", {}).get("error") or "WAVE analysis was unsuccessful."
        logger.warning("WAVE unsuccessful for %s: %s", url, reason)
        raise WaveAPIError(str(reason), extra={"wave_status": data.get("status")})

    return data


def _wcag_level(*, total_errors: int, total_contrast_errors: int) -> str | None:
    """Estimate a WCAG conformance level from the error counts.

    WAVE does not certify a conformance level, so this is a pragmatic heuristic:
    any errors -> fails (None); only contrast errors -> A; otherwise AA.
    """
    if total_errors > 0:
        return None
    if total_contrast_errors > 0:
        return "A"
    return "AA"


def parse_wave(raw: dict) -> dict:
    """Flatten a WAVE payload into ``{totals, wcag_level, issues}``.

    ``totals`` maps directly onto ``AccessibilityAudit`` fields; ``issues`` is a
    list of dicts ready to build :class:`AuditIssue` rows.
    """
    categories = raw.get("categories", {})

    totals = {
        "total_errors": 0,
        "total_alerts": 0,
        "total_features": 0,
        "total_structural": 0,
        "total_contrast_errors": 0,
    }
    issues: list[dict] = []

    for wave_category, (issue_type, total_field) in WAVE_CATEGORY_MAP.items():
        category = categories.get(wave_category, {}) or {}
        totals[total_field] = int(category.get("count", 0) or 0)

        for wave_id, item in (category.get("items", {}) or {}).items():
            issues.append(
                {
                    "issue_type": issue_type,
                    "wave_id": item.get("id", wave_id),
                    "description": item.get("description", ""),
                    "count": int(item.get("count", 0) or 0),
                    "wcag_reference": None,
                }
            )

    return {
        "totals": totals,
        "wcag_level": _wcag_level(
            total_errors=totals["total_errors"],
            total_contrast_errors=totals["total_contrast_errors"],
        ),
        "issues": issues,
    }
