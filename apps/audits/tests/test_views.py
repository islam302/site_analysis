"""Integration tests for the audits API."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.audits.constants import AuditStatus, IssueType
from apps.audits.models import AccessibilityAudit
from apps.audits.tests.factories import (
    AuditIssueFactory,
    CompletedAuditFactory,
    fake_wave_payload,
)
from apps.credits.tests.factories import set_balance
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


def test_run_anonymous_no_credits_needed(mocker):
    # Audits are public: anonymous users run without credits (user=None).
    mocker.patch(
        "apps.audits.services.audit_service.fetch_wave",
        return_value=fake_wave_payload(errors=1, contrast=0),
    )
    resp = APIClient().post(reverse("audits:run"), {"url": "https://example.com"}, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    audit = AccessibilityAudit.objects.get(id=resp.data["id"])
    assert audit.user_id is None
    assert audit.credits_consumed == 0


def test_run_audit_success(auth_client, mocker):
    set_balance(auth_client.user, 5)
    mocker.patch(
        "apps.audits.services.audit_service.fetch_wave",
        return_value=fake_wave_payload(errors=2, contrast=1),
    )
    resp = auth_client.post(reverse("audits:run"), {"url": "https://example.com"}, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["status"] == AuditStatus.COMPLETED
    assert resp.data["total_errors"] == 2
    assert len(resp.data["issues"]) >= 1


def test_run_audit_insufficient_credits(auth_client, mocker):
    wave = mocker.patch("apps.audits.services.audit_service.fetch_wave")
    resp = auth_client.post(reverse("audits:run"), {"url": "https://example.com"}, format="json")
    assert resp.status_code == status.HTTP_402_PAYMENT_REQUIRED
    wave.assert_not_called()


def test_list_audits_only_own(auth_client):
    CompletedAuditFactory(user=auth_client.user)
    CompletedAuditFactory()
    resp = auth_client.get(reverse("audits:audit-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_retrieve_audit_detail_with_issues(auth_client):
    audit = CompletedAuditFactory(user=auth_client.user)
    AuditIssueFactory(audit=audit, issue_type=IssueType.ERROR)
    resp = auth_client.get(reverse("audits:audit-detail", args=[audit.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["id"] == str(audit.id)
    assert len(resp.data["issues"]) == 1


def test_audit_issues_endpoint_filtered_by_type(auth_client):
    audit = CompletedAuditFactory(user=auth_client.user)
    AuditIssueFactory(audit=audit, issue_type=IssueType.ERROR, wave_id="alt_missing")
    AuditIssueFactory(audit=audit, issue_type=IssueType.ALERT, wave_id="redundant_alt")

    resp = auth_client.get(reverse("audits:issues", args=[audit.id]), {"issue_type": "error"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["issue_type"] == "error"


def test_delete_audit_soft_deletes(auth_client):
    audit = CompletedAuditFactory(user=auth_client.user)
    resp = auth_client.delete(reverse("audits:audit-detail", args=[audit.id]))
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    audit.refresh_from_db()
    assert audit.is_deleted is True


def test_list_filter_by_wcag_level(auth_client):
    CompletedAuditFactory(user=auth_client.user, wcag_level="AA", total_errors=0)
    CompletedAuditFactory(user=auth_client.user, wcag_level=None)
    resp = auth_client.get(reverse("audits:audit-list"), {"wcag_level": "AA"})
    assert resp.data["count"] == 1
