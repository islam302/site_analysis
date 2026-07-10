"""Tests for the combined speed_test service and status rollup."""
import pytest

from apps.analysis.constants import ReportStatus as GoogleStatus
from apps.analysis.models import AnalysisReport
from apps.gtmetrix.constants import ReportStatus as GTmetrixStatus
from apps.gtmetrix.models import GTmetrixReport
from apps.speed_test.models import SpeedTest
from apps.speed_test.services import submit_speed_test
from apps.speed_test.tests.factories import SpeedTestFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_submit_speed_test_creates_both_reports(django_capture_on_commit_callbacks):
    user = UserFactory()
    with django_capture_on_commit_callbacks(execute=False):
        st = submit_speed_test(user=user, url="https://example.com", strategy="mobile")

    assert SpeedTest.objects.filter(id=st.id).exists()
    assert st.google_report is not None
    assert st.gtmetrix_report is not None
    assert AnalysisReport.objects.filter(user=user).count() == 1
    assert GTmetrixReport.objects.filter(user=user).count() == 1
    assert st.combined_status == "pending"


def test_combined_status_completed():
    st = SpeedTestFactory(
        google_report__status=GoogleStatus.COMPLETED,
        gtmetrix_report__status=GTmetrixStatus.COMPLETED,
    )
    assert st.combined_status == "completed"


def test_combined_status_partial_when_one_pending():
    st = SpeedTestFactory(
        google_report__status=GoogleStatus.COMPLETED,
        gtmetrix_report__status=GTmetrixStatus.PENDING,
    )
    assert st.combined_status == "partial"


def test_combined_status_failed_when_both_failed():
    st = SpeedTestFactory(
        google_report__status=GoogleStatus.FAILED,
        gtmetrix_report__status=GTmetrixStatus.FAILED,
    )
    assert st.combined_status == "failed"
