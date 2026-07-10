"""Read-only queries for SSL reports."""
from __future__ import annotations

import uuid

from django.db.models import QuerySet

from apps.ssl_check.exceptions import SSLReportNotFoundError
from apps.ssl_check.models import SSLReport


def get_user_ssl_reports(*, user) -> QuerySet[SSLReport]:
    """Return the user's SSL reports, newest first."""
    return SSLReport.objects.filter(user=user).order_by("-created_at")


def get_ssl_report_by_id(*, report_id: uuid.UUID | str) -> SSLReport:
    """Return any SSL report by id (public read by UUID) or raise not-found."""
    try:
        return SSLReport.objects.get(id=report_id)
    except (SSLReport.DoesNotExist, ValueError, TypeError):
        raise SSLReportNotFoundError(extra={"report_id": str(report_id)})
