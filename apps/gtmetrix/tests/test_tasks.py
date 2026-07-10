"""Tests for the GTmetrix Celery task (eager under test settings)."""
import uuid

import pytest

from apps.gtmetrix.constants import ReportStatus
from apps.gtmetrix.exceptions import GTmetrixClientError
from apps.gtmetrix.tasks import run_gtmetrix_analysis
from apps.gtmetrix.tests.factories import GTmetrixReportFactory, fake_gtmetrix_result

pytestmark = pytest.mark.django_db


def test_run_gtmetrix_analysis_completes(mocker):
    report = GTmetrixReportFactory(status=ReportStatus.PENDING)
    mocker.patch("apps.gtmetrix.services.gtmetrix_service.start_test", return_value="test_abc")
    mocker.patch(
        "apps.gtmetrix.services.gtmetrix_service.poll_and_fetch",
        return_value=fake_gtmetrix_result(),
    )
    result_status = run_gtmetrix_analysis(report_id=str(report.id))
    assert result_status == ReportStatus.COMPLETED
    report.refresh_from_db()
    assert report.performance_score == 95


def test_run_gtmetrix_analysis_missing_report_is_safe():
    assert run_gtmetrix_analysis(report_id=str(uuid.uuid4())) == "missing"


def test_run_gtmetrix_analysis_client_error_stops_without_retry(mocker):
    report = GTmetrixReportFactory(status=ReportStatus.PENDING)
    # A 4xx (e.g. out of credits) must stop immediately, not retry.
    mocker.patch(
        "apps.gtmetrix.services.gtmetrix_service.start_test",
        side_effect=GTmetrixClientError("GTmetrix error 403: no credits"),
    )
    result = run_gtmetrix_analysis(report_id=str(report.id))
    assert result == "failed"
    report.refresh_from_db()
    assert report.status == ReportStatus.FAILED
    assert "403" in report.error_message
