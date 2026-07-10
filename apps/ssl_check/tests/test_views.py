"""Integration tests for the SSL check API endpoints."""
import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.ssl_check.models import SSLReport
from apps.ssl_check.tasks import run_ssl_scan_task
from apps.ssl_check.tests.factories import (
    CompletedSSLReportFactory,
    SSLReportFactory,
    fake_ssl_scan_result,
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


def test_analyze_creates_pending_public():
    resp = APIClient().post(
        reverse("ssl_check:analyze"), {"url": "https://example.com"}, format="json"
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.data["host"] == "example.com"
    assert SSLReport.objects.filter(user__isnull=True).count() == 1


def test_task_completes(mocker):
    report = SSLReportFactory()
    mocker.patch(
        "apps.ssl_check.services.ssl_service.run_ssl_scan",
        return_value=fake_ssl_scan_result("A"),
    )
    assert run_ssl_scan_task(report_id=str(report.id)) == "completed"
    report.refresh_from_db()
    assert report.grade == "A"


def test_task_missing_is_safe():
    assert run_ssl_scan_task(report_id=str(uuid.uuid4())) == "missing"


def test_list_reports_only_own(auth_client):
    CompletedSSLReportFactory(user=auth_client.user)
    CompletedSSLReportFactory()
    resp = auth_client.get(reverse("ssl_check:report-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_detail_public_by_id():
    report = CompletedSSLReportFactory(user=None)
    resp = APIClient().get(reverse("ssl_check:report-detail", args=[report.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["grade"] == "A+"
    assert "raw_response" in resp.data


def test_filter_by_grade(auth_client):
    CompletedSSLReportFactory(user=auth_client.user, grade="A+")
    CompletedSSLReportFactory(user=auth_client.user, grade="B")
    resp = auth_client.get(reverse("ssl_check:report-list"), {"grade": "B"})
    assert resp.data["count"] == 1


def test_delete_soft_deletes(auth_client):
    report = SSLReportFactory(user=auth_client.user)
    resp = auth_client.delete(reverse("ssl_check:report-detail", args=[report.id]))
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    report.refresh_from_db()
    assert report.is_deleted is True
