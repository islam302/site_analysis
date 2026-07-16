"""Run every analysis tool for one URL concurrently — without storing anything.

The three upstream tools (Google PageSpeed, GTmetrix, WAVE) are I/O-bound, so a
``ThreadPoolExecutor`` runs them in parallel; total wall-clock is the slowest
single tool rather than their sum. Each tool succeeds or fails independently and
nothing is persisted to the database — the result feeds straight into the PDF.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone

from apps.analysis.services.pagespeed_client import fetch_pagespeed, parse_pagespeed
from apps.audits.services.wave_client import fetch_wave, parse_wave
from apps.gtmetrix.services.gtmetrix_client import run_gtmetrix_test
from apps.linkchecker.services import quick_link_check
from apps.ssl_check.services.sslyze_scanner import run_ssl_scan
from apps.validator.services import quick_schema_check

logger = logging.getLogger("apps.full_report")


def _ok(data: dict) -> dict:
    return {"status": "ok", "data": data, "error": ""}


def _failed(exc: Exception) -> dict:
    return {"status": "failed", "data": {}, "error": str(exc)}


def _skipped() -> dict:
    """A tool disabled via ``settings.FULL_REPORT_TOOLS`` — not run at all."""
    return {"status": "skipped", "data": {}, "error": ""}


def _run_pagespeed(url: str, strategy: str) -> dict:
    try:
        raw = fetch_pagespeed(url=url, strategy=strategy)
        return _ok(parse_pagespeed(raw))
    except Exception as exc:  # noqa: BLE001 - report per-tool failure, don't abort
        logger.warning("PageSpeed failed in full report: %s", exc)
        return _failed(exc)


def _run_gtmetrix(url: str) -> dict:
    try:
        result = run_gtmetrix_test(url=url)
        return _ok(result["metrics"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("GTmetrix failed in full report: %s", exc)
        return _failed(exc)


def _run_wave(url: str) -> dict:
    try:
        parsed = parse_wave(fetch_wave(url=url))
        data = {
            **parsed["totals"],
            "wcag_level": parsed["wcag_level"],
            # Keep only the worst handful of issues for a readable summary.
            "top_issues": sorted(
                parsed["issues"], key=lambda i: i["count"], reverse=True
            )[:8],
        }
        return _ok(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("WAVE failed in full report: %s", exc)
        return _failed(exc)


def _run_ssl(url: str) -> dict:
    try:
        host = urlparse(url).hostname or url
        return _ok(run_ssl_scan(host=host))
    except Exception as exc:  # noqa: BLE001
        logger.warning("SSL scan failed in full report: %s", exc)
        return _failed(exc)


def _run_links(url: str) -> dict:
    try:
        return _ok(quick_link_check(url=url, max_links=1000))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Link check failed in full report: %s", exc)
        return _failed(exc)


def _run_schema(url: str) -> dict:
    try:
        return _ok(quick_schema_check(url=url))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Structured-data check failed in full report: %s", exc)
        return _failed(exc)


# Canonical tool key -> the callable that runs it (order = PDF section order).
_TOOL_RUNNERS = {
    "pagespeed": lambda url, strategy: _run_pagespeed(url, strategy),
    "gtmetrix": lambda url, strategy: _run_gtmetrix(url),
    "accessibility": lambda url, strategy: _run_wave(url),
    "ssl": lambda url, strategy: _run_ssl(url),
    "links": lambda url, strategy: _run_links(url),
    "structured_data": lambda url, strategy: _run_schema(url),
}


def enabled_tools() -> list[str]:
    """The tools enabled via ``settings.FULL_REPORT_TOOLS`` (invalid keys ignored)."""
    configured = {str(t).strip() for t in settings.FULL_REPORT_TOOLS}
    return [key for key in _TOOL_RUNNERS if key in configured]


def run_full_report(*, url: str, strategy: str) -> dict:
    """Run the enabled tools concurrently and return a combined dict.

    Which tools run is controlled by ``settings.FULL_REPORT_TOOLS``; any tool not
    listed there is marked ``"skipped"`` and never executed. Nothing is written to
    the database. The return value is consumed by :func:`build_report_pdf`.
    """
    active = enabled_tools()
    logger.info(
        "Full report started",
        extra={"url": url, "strategy": strategy, "tools": ",".join(active)},
    )

    report = {"url": url, "strategy": strategy, "generated_at": timezone.now()}

    with ThreadPoolExecutor(max_workers=max(1, len(active))) as pool:
        futures = {key: pool.submit(_TOOL_RUNNERS[key], url, strategy) for key in active}
        results = {key: future.result() for key, future in futures.items()}

    # Every canonical key is always present; disabled tools are "skipped".
    for key in _TOOL_RUNNERS:
        report[key] = results.get(key, _skipped())

    logger.info(
        "Full report finished",
        extra={"url": url, **{key: report[key]["status"] for key in _TOOL_RUNNERS}},
    )
    return report
