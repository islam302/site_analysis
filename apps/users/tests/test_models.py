"""Tests for the User model and manager."""
import pytest
from django.contrib.auth import get_user_model

from apps.users.tests.factories import UserFactory

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_create_user_hashes_password():
    user = User.objects.create_user(
        username="ada",
        email="a@example.com",
        password="TestPass123!",
        first_name="A",
        last_name="B",
    )
    assert user.password != "TestPass123!"
    assert user.check_password("TestPass123!")
    assert user.is_email_verified is False
    assert user.role == "user"


def test_create_superuser_flags_and_admin_role():
    admin = User.objects.create_superuser(
        username="root",
        email="admin@example.com",
        password="TestPass123!",
        first_name="Ad",
        last_name="Min",
    )
    assert admin.is_staff and admin.is_superuser and admin.is_email_verified
    assert admin.role == "admin"
    assert admin.is_admin is True


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user(
            username="x", email="", password="x", first_name="a", last_name="b"
        )


def test_email_is_normalized():
    user = User.objects.create_user(
        username="mixed",
        email="Mixed@EXAMPLE.COM",
        password="TestPass123!",
        first_name="A",
        last_name="B",
    )
    assert user.email == "Mixed@example.com"


def test_str_is_username_and_full_name():
    user = UserFactory(first_name="Jane", last_name="Doe", username="jane")
    assert str(user) == "jane"
    assert user.full_name == "Jane Doe"


def test_soft_delete_hides_from_default_manager():
    user = UserFactory()
    user.soft_delete()
    assert not User.objects.filter(id=user.id).exists()
    assert User.all_objects.filter(id=user.id).exists()
