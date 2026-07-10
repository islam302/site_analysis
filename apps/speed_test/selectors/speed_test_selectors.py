"""Read-only queries for combined speed tests."""
from __future__ import annotations

import uuid

from django.db.models import QuerySet

from apps.speed_test.exceptions import SpeedTestNotFoundError
from apps.speed_test.models import SpeedTest

_RELATED = ("google_report", "gtmetrix_report")


def get_user_speed_tests(*, user) -> QuerySet[SpeedTest]:
    """Return the user's speed tests with both sub-reports prefetched."""
    return (
        SpeedTest.objects.filter(user=user)
        .select_related(*_RELATED)
        .order_by("-created_at")
    )


def get_speed_test_detail(*, user, speed_test_id: uuid.UUID | str) -> SpeedTest:
    """Return one of the user's speed tests or raise not-found."""
    try:
        return (
            SpeedTest.objects.select_related(*_RELATED).get(user=user, id=speed_test_id)
        )
    except (SpeedTest.DoesNotExist, ValueError, TypeError):
        raise SpeedTestNotFoundError(extra={"speed_test_id": str(speed_test_id)})
