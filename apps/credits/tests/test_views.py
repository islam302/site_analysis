"""Integration tests for the credits API."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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


def test_balance_requires_auth():
    resp = APIClient().get(reverse("credits:balance"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_balance(auth_client):
    set_balance(auth_client.user, 25)
    resp = auth_client.get(reverse("credits:balance"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["balance"] == 25


def test_purchase_credits(auth_client):
    resp = auth_client.post(
        reverse("credits:purchase"), {"amount": 100, "description": "Starter pack"}, format="json"
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["balance"] == 100
    assert resp.data["total_purchased"] == 100


def test_purchase_rejects_non_positive(auth_client):
    resp = auth_client.post(reverse("credits:purchase"), {"amount": 0}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_transactions_list(auth_client):
    auth_client.post(reverse("credits:purchase"), {"amount": 10}, format="json")
    resp = auth_client.get(reverse("credits:transaction-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["transaction_type"] == "purchase"
