"""Business logic for the combined speed test.

Submitting a speed test creates one Google PageSpeed report and one GTmetrix
report for the same URL, dispatches both async pipelines, and links them under
a single :class:`SpeedTest` row.
"""
from __future__ import annotations

import logging

from django.db import transaction

from apps.analysis.services import submit_analysis
from apps.gtmetrix.services import submit_gtmetrix
from apps.speed_test.models import SpeedTest

logger = logging.getLogger("apps.speed_test")


def _resolve_user(user):
    return user if getattr(user, "is_authenticated", False) else None


@transaction.atomic
def submit_speed_test(*, user, url: str, strategy: str) -> SpeedTest:
    """Kick off both Google PageSpeed and GTmetrix analyses for ``url``.

    Both sub-analyses run asynchronously; the returned SpeedTest starts with
    two ``pending`` reports that populate independently.
    """
    google_report = submit_analysis(user=user, url=url, strategy=strategy)
    gtmetrix_report = submit_gtmetrix(user=user, url=url)

    speed_test = SpeedTest.objects.create(
        user=_resolve_user(user),
        url=url,
        strategy=strategy,
        google_report=google_report,
        gtmetrix_report=gtmetrix_report,
    )
    logger.info(
        "Speed test submitted",
        extra={
            "speed_test_id": str(speed_test.id),
            "google_report": str(google_report.id),
            "gtmetrix_report": str(gtmetrix_report.id),
        },
    )
    return speed_test
