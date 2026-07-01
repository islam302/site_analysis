"""Tests for API keys, X-API-Key auth, and admin user/key listing."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import ApiKey
from apps.users.tests.factories import DEFAULT_PASSWORD, StaffUserFactory, UserFactory

pytestmark = pytest.mark.django_db


def _bearer(client, user):
    login = client.post(
        reverse("users:login"),
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client


# --- model / signal ---------------------------------------------------------
def test_api_key_auto_created_for_new_user():
    user = UserFactory()
    assert ApiKey.objects.filter(user=user).exists()
    assert user.api_key.key.startswith("sk_")


def test_rotate_changes_key():
    user = UserFactory()
    old = user.api_key.key
    user.api_key.rotate()
    assert user.api_key.key != old


# --- own key endpoint -------------------------------------------------------
def test_get_my_api_key():
    client = _bearer(APIClient(), UserFactory())
    resp = client.get(reverse("users:my-api-key"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["key"].startswith("sk_")


def test_rotate_my_api_key():
    user = UserFactory()
    client = _bearer(APIClient(), user)
    old = user.api_key.key
    resp = client.post(reverse("users:my-api-key"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["key"] != old


def test_my_api_key_requires_auth():
    resp = APIClient().get(reverse("users:my-api-key"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# --- X-API-Key authentication ----------------------------------------------
def test_x_api_key_authenticates_request():
    user = UserFactory()
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=user.api_key.key)
    resp = client.get(reverse("users:me"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["email"] == user.email


def test_invalid_x_api_key_rejected():
    client = APIClient()
    client.credentials(HTTP_X_API_KEY="sk_not_a_real_key")
    resp = client.get(reverse("users:me"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# --- admin listing ----------------------------------------------------------
def test_admin_can_list_users_with_api_keys():
    admin = StaffUserFactory()
    UserFactory()
    UserFactory()
    client = _bearer(APIClient(), admin)

    resp = client.get(reverse("users:admin-user-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 3  # admin + 2 users
    # Each row exposes the user's API key.
    assert all("api_key" in row and row["api_key"]["key"] for row in resp.data["results"])


def test_non_admin_cannot_list_users():
    client = _bearer(APIClient(), UserFactory())  # role = user
    resp = client.get(reverse("users:admin-user-list"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_anonymous_cannot_list_users():
    resp = APIClient().get(reverse("users:admin-user-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_can_filter_users_by_role():
    admin = StaffUserFactory()
    UserFactory()
    client = _bearer(APIClient(), admin)
    resp = client.get(reverse("users:admin-user-list"), {"role": "admin"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == str(admin.id)
