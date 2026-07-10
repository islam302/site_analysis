"""Tests for the GTmetrix service layer and report parsing."""
import pytest

from apps.gtmetrix.constants import ReportStatus
from apps.gtmetrix.exceptions import GTmetrixAPIError
from apps.gtmetrix.models import GTmetrixReport
from apps.gtmetrix.services import process_gtmetrix, submit_gtmetrix
from apps.gtmetrix.services.gtmetrix_client import parse_report
from apps.gtmetrix.tests.factories import (
    GTmetrixReportFactory,
    fake_gtmetrix_result,
    fake_report_json,
)
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_submit_gtmetrix_creates_pending(django_capture_on_commit_callbacks):
    user = UserFactory()
    with django_capture_on_commit_callbacks(execute=False):
        report = submit_gtmetrix(user=user, url="https://example.com")
    assert report.status == ReportStatus.PENDING
    assert GTmetrixReport.objects.filter(id=report.id).exists()


def test_parse_report_maps_attributes():
    parsed = parse_report(fake_report_json())
    assert parsed["performance_score"] == 95
    assert parsed["gtmetrix_grade"] == "A"
    assert parsed["fully_loaded_time"] == 2500.0
    assert parsed["report_url"].endswith(".pdf")


def test_process_gtmetrix_success(mocker):
    report = GTmetrixReportFactory(status=ReportStatus.PENDING)
    mocker.patch("apps.gtmetrix.services.gtmetrix_service.start_test", return_value="test_abc")
    mocker.patch(
        "apps.gtmetrix.services.gtmetrix_service.poll_and_fetch",
        return_value=fake_gtmetrix_result(),
    )
    result = process_gtmetrix(report_id=str(report.id))

    result.refresh_from_db()
    assert result.status == ReportStatus.COMPLETED
    assert result.performance_score == 95
    assert result.gtmetrix_grade == "A"
    assert result.test_id == "test_abc"


def test_process_gtmetrix_failure_marks_failed_and_reraises(mocker):
    report = GTmetrixReportFactory(status=ReportStatus.PENDING)
    mocker.patch("apps.gtmetrix.services.gtmetrix_service.start_test", return_value="test_abc")
    mocker.patch(
        "apps.gtmetrix.services.gtmetrix_service.poll_and_fetch",
        side_effect=GTmetrixAPIError("boom"),
    )
    with pytest.raises(GTmetrixAPIError):
        process_gtmetrix(report_id=str(report.id))

    report.refresh_from_db()
    assert report.status == ReportStatus.FAILED
    assert "boom" in report.error_message
    # test_id is persisted before polling, so a retry resumes the same test.
    assert report.test_id == "test_abc"


def test_process_gtmetrix_retry_does_not_start_new_test(mocker):
    """A report that already has a test_id must not call start_test again."""
    report = GTmetrixReportFactory(status=ReportStatus.PENDING, test_id="existing_test")
    start = mocker.patch("apps.gtmetrix.services.gtmetrix_service.start_test")
    mocker.patch(
        "apps.gtmetrix.services.gtmetrix_service.poll_and_fetch",
        return_value=fake_gtmetrix_result(),
    )
    process_gtmetrix(report_id=str(report.id))
    start.assert_not_called()
