"""Tests for the analysis service layer and PageSpeed client parsing."""
import pytest

from apps.analysis.constants import ReportStatus, Strategy
from apps.analysis.exceptions import PageSpeedAPIError, PageSpeedConfigError
from apps.analysis.models import AnalysisHistory, AnalysisReport
from apps.analysis.services import process_analysis, submit_analysis
from apps.analysis.services.pagespeed_client import fetch_pagespeed, parse_pagespeed
from apps.analysis.tests.factories import AnalysisReportFactory, fake_pagespeed_payload
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


# --- submit -----------------------------------------------------------------
def test_submit_analysis_creates_pending_report(django_capture_on_commit_callbacks):
    user = UserFactory()
    with django_capture_on_commit_callbacks(execute=False):
        report = submit_analysis(user=user, url="https://example.com", strategy=Strategy.MOBILE)
    assert report.status == ReportStatus.PENDING
    assert AnalysisReport.objects.filter(id=report.id).exists()


# --- parser -----------------------------------------------------------------
def test_parse_pagespeed_extracts_scores_and_metrics():
    parsed = parse_pagespeed(fake_pagespeed_payload(performance=0.92, fcp_ms=1200.0))
    assert parsed["performance_score"] == 92
    assert parsed["seo_score"] == 100
    assert parsed["first_contentful_paint"] == 1.2  # ms -> s
    assert parsed["total_blocking_time"] == 150.0   # stays ms
    assert parsed["cumulative_layout_shift"] == 0.02


def test_parse_pagespeed_handles_missing_fields():
    parsed = parse_pagespeed({"lighthouseResult": {}})
    assert parsed["performance_score"] is None
    assert parsed["first_contentful_paint"] is None


# --- process ----------------------------------------------------------------
def test_process_analysis_success(mocker):
    report = AnalysisReportFactory(status=ReportStatus.PENDING)
    mocker.patch(
        "apps.analysis.services.analysis_service.fetch_pagespeed",
        return_value=fake_pagespeed_payload(),
    )
    result = process_analysis(report_id=str(report.id))

    result.refresh_from_db()
    assert result.status == ReportStatus.COMPLETED
    assert result.performance_score == 92
    # History rollup created/incremented.
    history = AnalysisHistory.objects.get(user=report.user, url=report.url)
    assert history.reports_count == 1


def test_process_analysis_increments_existing_history(mocker):
    user = UserFactory()
    r1 = AnalysisReportFactory(user=user, url="https://same.com")
    r2 = AnalysisReportFactory(user=user, url="https://same.com")
    mocker.patch(
        "apps.analysis.services.analysis_service.fetch_pagespeed",
        return_value=fake_pagespeed_payload(),
    )
    process_analysis(report_id=str(r1.id))
    process_analysis(report_id=str(r2.id))

    history = AnalysisHistory.objects.get(user=user, url="https://same.com")
    assert history.reports_count == 2


def test_process_analysis_marks_failed_and_reraises(mocker):
    report = AnalysisReportFactory(status=ReportStatus.PENDING)
    mocker.patch(
        "apps.analysis.services.analysis_service.fetch_pagespeed",
        side_effect=PageSpeedAPIError("boom"),
    )
    with pytest.raises(PageSpeedAPIError):
        process_analysis(report_id=str(report.id))

    report.refresh_from_db()
    assert report.status == ReportStatus.FAILED
    assert "boom" in report.error_message


# --- client config guard ----------------------------------------------------
def test_fetch_pagespeed_without_key_raises(settings):
    settings.GOOGLE_PAGESPEED_API_KEY = ""
    with pytest.raises(PageSpeedConfigError):
        fetch_pagespeed(url="https://example.com", strategy="mobile")


# --- retry on transient errors ----------------------------------------------
def _resp(status_code, json_body=None):
    """Build a fake requests.Response-like object for the client to consume."""
    import requests

    r = requests.Response()
    r.status_code = status_code
    if json_body is not None:
        import json as _json

        r._content = _json.dumps(json_body).encode()
    return r


def test_fetch_pagespeed_retries_transient_400_then_succeeds(mocker, settings):
    settings.GOOGLE_PAGESPEED_API_KEY = "k"
    settings.PAGESPEED_MAX_RETRIES = 2
    mocker.patch("apps.analysis.services.pagespeed_client.time.sleep")  # no real waiting
    ok = fake_pagespeed_payload()
    mocker.patch(
        "apps.analysis.services.pagespeed_client.requests.get",
        side_effect=[_resp(400, {"error": {"message": "Lighthouse timed out"}}),
                     _resp(200, ok)],
    )
    assert fetch_pagespeed(url="https://slow.example", strategy="desktop") == ok


def test_fetch_pagespeed_gives_up_after_retries_with_real_message(mocker, settings):
    settings.GOOGLE_PAGESPEED_API_KEY = "k"
    settings.PAGESPEED_MAX_RETRIES = 1
    sleep = mocker.patch("apps.analysis.services.pagespeed_client.time.sleep")
    mocker.patch(
        "apps.analysis.services.pagespeed_client.requests.get",
        return_value=_resp(500, {"error": {"message": "Backend error"}}),
    )
    with pytest.raises(PageSpeedAPIError) as exc:
        fetch_pagespeed(url="https://x.example", strategy="desktop")
    assert "Backend error" in str(exc.value)  # Google's real reason is surfaced
    assert sleep.call_count == 1  # 2 attempts -> slept once between them


def test_fetch_pagespeed_does_not_retry_non_retryable(mocker, settings):
    settings.GOOGLE_PAGESPEED_API_KEY = "k"
    settings.PAGESPEED_MAX_RETRIES = 3
    sleep = mocker.patch("apps.analysis.services.pagespeed_client.time.sleep")
    get = mocker.patch(
        "apps.analysis.services.pagespeed_client.requests.get",
        return_value=_resp(403, {"error": {"message": "API key invalid"}}),
    )
    with pytest.raises(PageSpeedAPIError):
        fetch_pagespeed(url="https://x.example", strategy="desktop")
    assert get.call_count == 1  # 403 is not transient -> no retry
    sleep.assert_not_called()
