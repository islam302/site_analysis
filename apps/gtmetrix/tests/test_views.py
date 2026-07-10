"""Integration tests for the GTmetrix API endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.gtmetrix.models import GTmetrixReport
from apps.gtmetrix.tests.factories import (
    CompletedGTmetrixReportFactory,
    GTmetrixReportFactory,
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


def test_analyze_allows_anonymous():
    resp = APIClient().post(
        reverse("gtmetrix:analyze"), {"url": "https://example.com"}, format="json"
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert GTmetrixReport.objects.filter(user__isnull=True).count() == 1


def test_analyze_creates_pending_report(auth_client, mocker):
    mocker.patch("apps.gtmetrix.services.gtmetrix_service.start_test", return_value="t")
    mocker.patch(
        "apps.gtmetrix.services.gtmetrix_service.poll_and_fetch",
        return_value={"test_id": "t", "metrics": {}, "raw": {}},
    )
    resp = auth_client.post(
        reverse("gtmetrix:analyze"), {"url": "https://example.com"}, format="json"
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert GTmetrixReport.objects.filter(user=auth_client.user).count() == 1


def test_list_reports_only_own(auth_client):
    CompletedGTmetrixReportFactory(user=auth_client.user)
    CompletedGTmetrixReportFactory()
    resp = auth_client.get(reverse("gtmetrix:report-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_retrieve_report_detail(auth_client):
    report = CompletedGTmetrixReportFactory(user=auth_client.user)
    resp = auth_client.get(reverse("gtmetrix:report-detail", args=[report.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["gtmetrix_grade"] == "A"
    assert "raw_response" in resp.data


def test_delete_report_soft_deletes(auth_client):
    report = GTmetrixReportFactory(user=auth_client.user)
    resp = auth_client.delete(reverse("gtmetrix:report-detail", args=[report.id]))
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    report.refresh_from_db()
    assert report.is_deleted is True


def test_filter_reports_by_grade(auth_client):
    CompletedGTmetrixReportFactory(user=auth_client.user, gtmetrix_grade="A")
    CompletedGTmetrixReportFactory(user=auth_client.user, gtmetrix_grade="B")
    resp = auth_client.get(reverse("gtmetrix:report-list"), {"grade": "A"})
    assert resp.data["count"] == 1
