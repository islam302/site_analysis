"""Integration tests for the auth API endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import DEFAULT_PASSWORD, UnverifiedUserFactory, UserFactory
from apps.users.tokens import make_email_verification_token

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def auth_client(client):
    user = UserFactory()
    login = client.post(
        reverse("users:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    client.user = user
    return client


def test_register_returns_tokens_and_user(client):
    resp = client.post(
        reverse("users:register"),
        {
            "username": "freshuser",
            "email": "fresh@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "Fresh",
            "last_name": "User",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert {"access", "refresh", "user"} <= set(resp.data)
    assert resp.data["user"]["is_email_verified"] is False
    assert resp.data["user"]["username"] == "freshuser"
    assert resp.data["user"]["role"] == "user"


def test_register_password_mismatch(client):
    resp = client.post(
        reverse("users:register"),
        {
            "username": "freshuser",
            "email": "fresh@example.com",
            "password": "StrongPass123!",
            "password_confirm": "Different123!",
            "first_name": "Fresh",
            "last_name": "User",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_login_success(client):
    user = UserFactory()
    resp = client.post(
        reverse("users:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["user"]["email"] == user.email


def test_login_invalid_credentials(client):
    user = UserFactory()
    resp = client.post(
        reverse("users:login"),
        {"email": user.email, "password": "WrongPass123!"},
        format="json",
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert "error" in resp.data


def test_me_requires_authentication(client):
    resp = client.get(reverse("users:me"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_get_and_patch(auth_client):
    resp = auth_client.get(reverse("users:me"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["email"] == auth_client.user.email

    patch = auth_client.patch(reverse("users:me"), {"first_name": "Renamed"}, format="json")
    assert patch.status_code == status.HTTP_200_OK
    assert patch.data["first_name"] == "Renamed"


def test_verify_email_endpoint(client):
    user = UnverifiedUserFactory()
    token = make_email_verification_token(user)
    resp = client.post(reverse("users:email-verify"), {"token": token}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.is_email_verified is True


def test_logout_blacklists_refresh(client):
    user = UserFactory()
    login = client.post(
        reverse("users:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )
    refresh = login.data["refresh"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    resp = client.post(reverse("users:logout"), {"refresh": refresh}, format="json")
    assert resp.status_code == status.HTTP_205_RESET_CONTENT

    # The blacklisted refresh token can no longer be used.
    refreshed = client.post(reverse("users:token-refresh"), {"refresh": refresh}, format="json")
    assert refreshed.status_code == status.HTTP_401_UNAUTHORIZED


def test_password_reset_request_always_ok(client):
    resp = client.post(
        reverse("users:password-reset"),
        {"email": "ghost@example.com"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
