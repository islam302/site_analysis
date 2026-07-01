"""Tests for user selectors."""
import uuid

import pytest

from apps.users.exceptions import UserNotFoundError
from apps.users.selectors import get_user_by_email, get_user_by_id
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_get_user_by_id_returns_user():
    user = UserFactory()
    assert get_user_by_id(user_id=user.id) == user


def test_get_user_by_id_missing_raises():
    with pytest.raises(UserNotFoundError):
        get_user_by_id(user_id=uuid.uuid4())


def test_get_user_by_email_case_insensitive_domain():
    user = UserFactory(email="person@example.com")
    assert get_user_by_email(email="person@EXAMPLE.COM") == user


def test_get_user_by_email_missing_returns_none():
    assert get_user_by_email(email="nobody@example.com") is None
