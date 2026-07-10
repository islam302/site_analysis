"""Tests for GTmetrix selectors."""
import uuid

import pytest

from apps.gtmetrix.exceptions import GTmetrixReportNotFoundError
from apps.gtmetrix.selectors import get_gtmetrix_report_detail, get_user_gtmetrix_reports
from apps.gtmetrix.tests.factories import GTmetrixReportFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_get_user_reports_only_own():
    user = UserFactory()
    GTmetrixReportFactory(user=user)
    GTmetrixReportFactory()
    assert get_user_gtmetrix_reports(user=user).count() == 1


def test_get_report_detail_found():
    report = GTmetrixReportFactory()
    assert get_gtmetrix_report_detail(user=report.user, report_id=report.id) == report


def test_get_report_detail_not_found():
    with pytest.raises(GTmetrixReportNotFoundError):
        get_gtmetrix_report_detail(user=UserFactory(), report_id=uuid.uuid4())
