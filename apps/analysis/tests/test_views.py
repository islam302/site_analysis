"""Integration tests for the analysis API endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.analysis.constants import ReportStatus, Strategy
from apps.analysis.models import AnalysisReport
from apps.analysis.tests.factories import (
    AnalysisHistoryFactory,
    AnalysisReportFactory,
    CompletedReportFactory,
    fake_pagespeed_payload,
)
from apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    client = APIClient()
    user = UserFactory()
    login = client.post(
        reverse("users:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    client.user = user
    return client


def test_reports_list_anonymous_is_empty():
    # Reports list is public but scoped to the user; anonymous sees nothing.
    resp = APIClient().get(reverse("analysis:report-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_report_detail_public_by_id():
    # Anyone with the UUID can poll a report (needed for anonymous submissions).
    report = CompletedReportFactory(user=None)
    resp = APIClient().get(reverse("analysis:report-detail", args=[report.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["id"] == str(report.id)


def test_analyze_creates_pending_report(auth_client, mocker):
    # Prevent the eager Celery task from calling the real API.
    mocker.patch(
        "apps.analysis.services.analysis_service.fetch_pagespeed",
        return_value=fake_pagespeed_payload(),
    )
    resp = auth_client.post(
        reverse("analysis:analyze"),
        {"url": "https://example.com", "strategy": Strategy.MOBILE},
        format="json",
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.data["url"] == "https://example.com"
    assert AnalysisReport.objects.filter(user=auth_client.user).count() == 1


def test_analyze_allows_anonymous_submission(mocker):
    """AnalyzeView permits anonymous users; the report is stored with user=None."""
    mocker.patch(
        "apps.analysis.services.analysis_service.fetch_pagespeed",
        return_value=fake_pagespeed_payload(),
    )
    resp = APIClient().post(
        reverse("analysis:analyze"),
        {"url": "https://example.com", "strategy": "desktop"},
        format="json",
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    report = AnalysisReport.objects.get(id=resp.data["id"])
    assert report.user_id is None


def test_analyze_rejects_localhost(auth_client):
    resp = auth_client.post(
        reverse("analysis:analyze"),
        {"url": "http://localhost:8000", "strategy": Strategy.MOBILE},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_list_reports_only_shows_own(auth_client):
    CompletedReportFactory(user=auth_client.user)
    CompletedReportFactory()  # other user
    resp = auth_client.get(reverse("analysis:report-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_list_reports_filter_by_strategy(auth_client):
    CompletedReportFactory(user=auth_client.user, strategy=Strategy.MOBILE)
    CompletedReportFactory(user=auth_client.user, strategy=Strategy.DESKTOP)
    resp = auth_client.get(reverse("analysis:report-list"), {"strategy": Strategy.DESKTOP})
    assert resp.data["count"] == 1


def test_list_reports_ordering_by_score(auth_client):
    CompletedReportFactory(user=auth_client.user, performance_score=50)
    CompletedReportFactory(user=auth_client.user, performance_score=90)
    resp = auth_client.get(reverse("analysis:report-list"), {"ordering": "-performance_score"})
    scores = [r["performance_score"] for r in resp.data["results"]]
    assert scores == [90, 50]


def test_retrieve_report_detail(auth_client):
    report = CompletedReportFactory(user=auth_client.user)
    resp = auth_client.get(reverse("analysis:report-detail", args=[report.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["id"] == str(report.id)
    assert "raw_response" in resp.data


def test_delete_report_soft_deletes(auth_client):
    report = AnalysisReportFactory(user=auth_client.user)
    resp = auth_client.delete(reverse("analysis:report-detail", args=[report.id]))
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    report.refresh_from_db()
    assert report.is_deleted is True
    # No longer visible via the default manager / list endpoint.
    assert not AnalysisReport.objects.filter(id=report.id).exists()


def test_history_endpoint(auth_client):
    AnalysisHistoryFactory(user=auth_client.user, reports_count=3)
    resp = auth_client.get(reverse("analysis:history"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["reports_count"] == 3


