"""Integration tests for the combined speed_test API endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.speed_test.models import SpeedTest
from apps.speed_test.tests.factories import CompletedSpeedTestFactory, SpeedTestFactory
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
        reverse("speed_test:analyze"),
        {"url": "https://example.com", "strategy": "mobile"},
        format="json",
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert SpeedTest.objects.filter(user__isnull=True).count() == 1


def test_analyze_creates_combined_test(auth_client, mocker):
    mocker.patch(
        "apps.analysis.services.analysis_service.fetch_pagespeed",
        return_value={"lighthouseResult": {}},
    )
    mocker.patch("apps.gtmetrix.services.gtmetrix_service.start_test", return_value="t")
    mocker.patch(
        "apps.gtmetrix.services.gtmetrix_service.poll_and_fetch",
        return_value={"test_id": "t", "metrics": {}, "raw": {}},
    )
    resp = auth_client.post(
        reverse("speed_test:analyze"),
        {"url": "https://example.com", "strategy": "desktop"},
        format="json",
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.data["google_report"] is not None
    assert resp.data["gtmetrix_report"] is not None
    assert resp.data["combined_status"] in ("pending", "partial", "completed")
    assert SpeedTest.objects.filter(user=auth_client.user).count() == 1


def test_list_speed_tests_only_own(auth_client):
    CompletedSpeedTestFactory(user=auth_client.user)
    CompletedSpeedTestFactory()
    resp = auth_client.get(reverse("speed_test:report-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_retrieve_speed_test_detail(auth_client):
    st = CompletedSpeedTestFactory(user=auth_client.user)
    resp = auth_client.get(reverse("speed_test:report-detail", args=[st.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["combined_status"] == "completed"
    assert resp.data["google_report"]["performance_score"] is not None
    assert resp.data["gtmetrix_report"]["gtmetrix_grade"] == "A"


def test_delete_speed_test_soft_deletes(auth_client):
    st = SpeedTestFactory(user=auth_client.user)
    resp = auth_client.delete(reverse("speed_test:report-detail", args=[st.id]))
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    st.refresh_from_db()
    assert st.is_deleted is True
