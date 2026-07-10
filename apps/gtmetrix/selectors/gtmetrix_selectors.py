"""Read-only queries for GTmetrix reports."""
from __future__ import annotations

import uuid

from django.db.models import QuerySet

from apps.gtmetrix.exceptions import GTmetrixReportNotFoundError
from apps.gtmetrix.models import GTmetrixReport


def get_user_gtmetrix_reports(*, user) -> QuerySet[GTmetrixReport]:
    """Return the user's GTmetrix reports, newest first."""
    return GTmetrixReport.objects.filter(user=user).order_by("-created_at")


def get_gtmetrix_report_detail(*, user, report_id: uuid.UUID | str) -> GTmetrixReport:
    """Return a single report owned by ``user`` or raise not-found."""
    try:
        return GTmetrixReport.objects.get(user=user, id=report_id)
    except (GTmetrixReport.DoesNotExist, ValueError, TypeError):
        raise GTmetrixReportNotFoundError(extra={"report_id": str(report_id)})
