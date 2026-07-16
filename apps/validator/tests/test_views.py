"""Integration tests for the validator API (auth, ownership, filters)."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory
from apps.validator.constants import IssueSeverity, SchemaFormat, ValidationStatus
from apps.validator.models import ValidationJob
from apps.validator.tests import fixtures as fx
from apps.validator.tests.factories import (
    SchemaIssueFactory,
    SchemaItemFactory,
    ValidationJobFactory,
)

pytestmark = pytest.mark.django_db


def _login(client, user):
    resp = client.post(
        reverse("users:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")


@pytest.fixture
def auth_client():
    client = APIClient()
    user = UserFactory()
    _login(client, user)
    client.user = user
    return client


# --- auth -------------------------------------------------------------------
def test_validate_requires_auth():
    resp = APIClient().post(reverse("validator:validate"), {"url": "https://a.example"}, format="json")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_requires_auth():
    assert APIClient().get(reverse("validator:validation-list")).status_code == (
        status.HTTP_401_UNAUTHORIZED
    )


# --- submit -----------------------------------------------------------------
def test_submit_returns_202_and_persists(auth_client, mocker):
    mocker.patch(
        "apps.validator.services.validation_service.fetch_page", return_value=fx.ORG_VALID
    )
    resp = auth_client.post(
        reverse("validator:validate"), {"url": "https://acme.example"}, format="json"
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.data["status"] == ValidationStatus.PENDING
    job = ValidationJob.objects.get(id=resp.data["id"])
    assert job.user == auth_client.user


def test_submit_validates_url(auth_client):
    resp = auth_client.post(reverse("validator:validate"), {"url": "not-a-url"}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_submit_rejects_localhost(auth_client):
    resp = auth_client.post(
        reverse("validator:validate"), {"url": "http://localhost/x"}, format="json"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --- list / retrieve --------------------------------------------------------
def test_list_only_shows_own_jobs(auth_client):
    ValidationJobFactory(user=auth_client.user)
    ValidationJobFactory()  # someone else's

    resp = auth_client.get(reverse("validator:validation-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_retrieve_other_users_job_is_404(auth_client):
    other = ValidationJobFactory()
    resp = auth_client.get(reverse("validator:validation-detail", args=[other.id]))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_includes_schemas_and_issues(auth_client):
    job = ValidationJobFactory(user=auth_client.user, total_schemas_found=1)
    item = SchemaItemFactory(job=job, schema_type="Product", is_valid=False)
    SchemaIssueFactory(schema_item=item, field="image", severity=IssueSeverity.ERROR)

    resp = auth_client.get(reverse("validator:validation-detail", args=[job.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data["schemas"]) == 1
    assert resp.data["schemas"][0]["schema_type"] == "Product"
    assert resp.data["schemas"][0]["issues"][0]["field"] == "image"


# --- sub-resources + filters ------------------------------------------------
def test_schemas_endpoint_filters(auth_client):
    job = ValidationJobFactory(user=auth_client.user)
    SchemaItemFactory(job=job, schema_type="Product", format=SchemaFormat.JSON_LD, is_valid=True)
    SchemaItemFactory(job=job, schema_type="Article", format=SchemaFormat.MICRODATA, is_valid=False)

    base = reverse("validator:validation-schemas", args=[job.id])
    assert auth_client.get(base).data["count"] == 2
    assert auth_client.get(base, {"schema_type": "product"}).data["count"] == 1
    assert auth_client.get(base, {"format": "microdata"}).data["count"] == 1
    assert auth_client.get(base, {"is_valid": "false"}).data["count"] == 1


def test_issues_endpoint_filters_by_severity(auth_client):
    job = ValidationJobFactory(user=auth_client.user)
    item = SchemaItemFactory(job=job)
    SchemaIssueFactory(schema_item=item, severity=IssueSeverity.ERROR, field="image")
    SchemaIssueFactory(schema_item=item, severity=IssueSeverity.WARNING, field="offers")

    base = reverse("validator:validation-issues", args=[job.id])
    assert auth_client.get(base).data["count"] == 2
    assert auth_client.get(base, {"severity": "error"}).data["count"] == 1
    assert auth_client.get(base, {"severity": "warning"}).data["count"] == 1


def test_schemas_of_other_users_job_is_404(auth_client):
    other = ValidationJobFactory()
    resp = auth_client.get(reverse("validator:validation-schemas", args=[other.id]))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
