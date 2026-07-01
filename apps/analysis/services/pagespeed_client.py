"""Thin client for the Google PageSpeed Insights v5 API.

Responsible for two pure concerns:
1. Performing the HTTP request (:func:`fetch_pagespeed`).
2. Parsing the Lighthouse payload into our flat metric schema
   (:func:`parse_pagespeed`).

No database access happens here — the service layer persists results.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

from apps.analysis.constants import (
    AUDIT_TO_FIELD,
    CATEGORY_TO_FIELD,
    PAGESPEED_CATEGORIES,
)
from apps.analysis.exceptions import PageSpeedAPIError, PageSpeedConfigError

logger = logging.getLogger("apps.analysis")

PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def fetch_pagespeed(*, url: str, strategy: str, timeout: int | None = None) -> dict:
    """Call the PageSpeed Insights API and return the raw JSON response.

    Raises:
        PageSpeedConfigError: if no API key is configured.
        PageSpeedAPIError: on network errors, non-2xx responses, or bad JSON.
    """
    api_key = settings.GOOGLE_PAGESPEED_API_KEY
    if not api_key:
        raise PageSpeedConfigError()

    params = [
        ("url", url),
        ("strategy", strategy),
        ("key", api_key),
    ]
    # ``category`` is repeated once per Lighthouse category we want scored.
    params += [("category", category) for category in PAGESPEED_CATEGORIES]

    timeout = timeout or settings.PAGESPEED_REQUEST_TIMEOUT
    try:
        response = requests.get(PAGESPEED_ENDPOINT, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        logger.warning(
            "PageSpeed API HTTP error",
            extra={"url": url, "strategy": strategy, "status_code": status_code},
        )
        raise PageSpeedAPIError(
            "PageSpeed Insights returned an error response.",
            extra={"status_code": status_code},
        )
    except (requests.RequestException, ValueError) as exc:
        # ValueError covers .json() decode failures.
        logger.warning(
            "PageSpeed API request failed",
            extra={"url": url, "strategy": strategy, "error": str(exc)},
        )
        raise PageSpeedAPIError(extra={"error": str(exc)})


def _convert(numeric_value: float | None, unit: str) -> float | None:
    if numeric_value is None:
        return None
    if unit == "ms_to_s":
        return round(numeric_value / 1000.0, 3)
    if unit == "ms":
        return round(numeric_value, 2)
    return round(numeric_value, 4)  # "raw" (e.g. CLS)


def parse_pagespeed(raw: dict) -> dict:
    """Flatten a Lighthouse payload into our model field schema.

    Returns a dict with keys matching ``AnalysisReport`` fields. Missing audits
    or categories yield ``None`` rather than raising, so a partial response is
    still persistable.
    """
    lighthouse = raw.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    audits = lighthouse.get("audits", {})

    parsed: dict[str, float | int | None] = {}

    for category_key, field in CATEGORY_TO_FIELD.items():
        score = categories.get(category_key, {}).get("score")
        parsed[field] = round(score * 100) if isinstance(score, (int, float)) else None

    for audit_key, (field, unit) in AUDIT_TO_FIELD.items():
        numeric_value = audits.get(audit_key, {}).get("numericValue")
        parsed[field] = _convert(numeric_value, unit)

    return parsed
