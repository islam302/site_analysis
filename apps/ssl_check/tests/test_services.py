"""Tests for the SSL service layer and grade synthesis."""
import pytest

from apps.ssl_check.constants import ReportStatus
from apps.ssl_check.exceptions import SSLScanError
from apps.ssl_check.models import SSLReport
from apps.ssl_check.services import process_ssl_check, submit_ssl_check
from apps.ssl_check.services.sslyze_scanner import _synthesise_grade
from apps.ssl_check.tests.factories import SSLReportFactory, fake_ssl_scan_result
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_submit_derives_host_and_creates_pending(django_capture_on_commit_callbacks):
    user = UserFactory()
    with django_capture_on_commit_callbacks(execute=False):
        report = submit_ssl_check(user=user, url="https://www.example.com/path")
    assert report.status == ReportStatus.PENDING
    assert report.host == "www.example.com"


def test_process_success_sets_grade_and_cert(mocker):
    report = SSLReportFactory(status=ReportStatus.PENDING)
    mocker.patch(
        "apps.ssl_check.services.ssl_service.run_ssl_scan",
        return_value=fake_ssl_scan_result("A+"),
    )
    result = process_ssl_check(report_id=str(report.id))

    result.refresh_from_db()
    assert result.status == ReportStatus.COMPLETED
    assert result.grade == "A+"
    assert result.protocols == ["TLS 1.2", "TLS 1.3"]
    assert result.cert_is_trusted is True


def test_process_failure_marks_failed_and_reraises(mocker):
    report = SSLReportFactory(status=ReportStatus.PENDING)
    mocker.patch(
        "apps.ssl_check.services.ssl_service.run_ssl_scan",
        side_effect=SSLScanError("could not connect"),
    )
    with pytest.raises(SSLScanError):
        process_ssl_check(report_id=str(report.id))

    report.refresh_from_db()
    assert report.status == ReportStatus.FAILED
    assert "could not connect" in report.error_message


# --- grade synthesis --------------------------------------------------------
def test_grade_modern_is_a_plus():
    grade = _synthesise_grade(
        protocols=["TLS 1.2", "TLS 1.3"], vulnerabilities={}, expires_in_days=90, is_trusted=True
    )
    assert grade == "A+"


def test_grade_weak_protocol_is_b():
    grade = _synthesise_grade(
        protocols=["TLS 1.0", "TLS 1.2"], vulnerabilities={}, expires_in_days=90, is_trusted=True
    )
    assert grade == "B"


def test_grade_insecure_ssl_is_f():
    grade = _synthesise_grade(
        protocols=["SSL 3.0", "TLS 1.2"], vulnerabilities={}, expires_in_days=90, is_trusted=True
    )
    assert grade == "F"


def test_grade_serious_vuln_is_f():
    grade = _synthesise_grade(
        protocols=["TLS 1.2"], vulnerabilities={"heartbleed": True}, expires_in_days=90, is_trusted=True
    )
    assert grade == "F"


def test_grade_untrusted_is_t():
    grade = _synthesise_grade(
        protocols=["TLS 1.2", "TLS 1.3"], vulnerabilities={}, expires_in_days=90, is_trusted=False
    )
    assert grade == "T"


def test_grade_expired_is_f():
    grade = _synthesise_grade(
        protocols=["TLS 1.2", "TLS 1.3"], vulnerabilities={}, expires_in_days=-5, is_trusted=True
    )
    assert grade == "F"
