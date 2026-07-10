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

from django.utils import timezone

from apps.analysis.services.pagespeed_client import fetch_pagespeed, parse_pagespeed
from apps.audits.services.wave_client import fetch_wave, parse_wave
from apps.gtmetrix.services.gtmetrix_client import run_gtmetrix_test
from apps.ssl_check.services.sslyze_scanner import run_ssl_scan

logger = logging.getLogger("apps.full_report")


def _ok(data: dict) -> dict:
    return {"status": "ok", "data": data, "error": ""}


def _failed(exc: Exception) -> dict:
    return {"status": "failed", "data": {}, "error": str(exc)}


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


def run_full_report(*, url: str, strategy: str) -> dict:
    """Run PageSpeed + GTmetrix + WAVE concurrently and return a combined dict.

    Nothing is written to the database. The return value is consumed by
    :func:`build_report_pdf`.
    """
    logger.info("Full report started", extra={"url": url, "strategy": strategy})

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_pagespeed = pool.submit(_run_pagespeed, url, strategy)
        f_gtmetrix = pool.submit(_run_gtmetrix, url)
        f_wave = pool.submit(_run_wave, url)
        f_ssl = pool.submit(_run_ssl, url)

        report = {
            "url": url,
            "strategy": strategy,
            "generated_at": timezone.now(),
            "pagespeed": f_pagespeed.result(),
            "gtmetrix": f_gtmetrix.result(),
            "accessibility": f_wave.result(),
            "ssl": f_ssl.result(),
        }

    logger.info(
        "Full report finished",
        extra={
            "url": url,
            "pagespeed": report["pagespeed"]["status"],
            "gtmetrix": report["gtmetrix"]["status"],
            "accessibility": report["accessibility"]["status"],
            "ssl": report["ssl"]["status"],
        },
    )
    return report
