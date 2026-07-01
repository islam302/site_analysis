"""Tests for the auth service layer."""
import pytest
from django.contrib.auth import get_user_model

from apps.common.exceptions import ApplicationError
from apps.users.exceptions import (
    EmailAlreadyRegisteredError,
    EmailAlreadyVerifiedError,
    InactiveAccountError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    UsernameAlreadyTakenError,
)
from apps.users.services import (
    change_password,
    confirm_password_reset,
    register_user,
    update_profile,
    verify_email,
)
from apps.users.services.auth_service import authenticate_user
from apps.users.tests.factories import DEFAULT_PASSWORD, UnverifiedUserFactory, UserFactory
from apps.users.tokens import (
    make_email_verification_token,
    make_password_reset_token,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# --- register ---------------------------------------------------------------
def test_register_user_creates_unverified_user():
    user = register_user(
        username="newbie",
        email="new@example.com",
        password="StrongPass123!",
        first_name="New",
        last_name="User",
    )
    assert user.is_email_verified is False
    assert user.check_password("StrongPass123!")
    assert user.username == "newbie"
    assert user.role == "user"


def test_register_user_duplicate_email_raises():
    UserFactory(email="dupe@example.com")
    with pytest.raises(EmailAlreadyRegisteredError):
        register_user(
            username="unique1",
            email="dupe@example.com",
            password="StrongPass123!",
            first_name="A",
            last_name="B",
        )


def test_register_user_duplicate_username_raises():
    UserFactory(username="taken")
    with pytest.raises(UsernameAlreadyTakenError):
        register_user(
            username="taken",
            email="fresh@example.com",
            password="StrongPass123!",
            first_name="A",
            last_name="B",
        )


def test_register_user_weak_password_raises():
    with pytest.raises(ApplicationError) as exc:
        register_user(
            username="weakling",
            email="weak@example.com",
            password="weak",
            first_name="A",
            last_name="B",
        )
    assert "password" in exc.value.extra


# --- authenticate -----------------------------------------------------------
def test_authenticate_user_success():
    user = UserFactory()
    assert authenticate_user(email=user.email, password=DEFAULT_PASSWORD) == user


def test_authenticate_user_bad_password():
    user = UserFactory()
    with pytest.raises(InvalidCredentialsError):
        authenticate_user(email=user.email, password="WrongPass123!")


def test_authenticate_inactive_user():
    user = UserFactory(is_active=False)
    with pytest.raises(InactiveAccountError):
        authenticate_user(email=user.email, password=DEFAULT_PASSWORD)


# --- verify email -----------------------------------------------------------
def test_verify_email_success():
    user = UnverifiedUserFactory()
    token = make_email_verification_token(user)
    verified = verify_email(token=token)
    assert verified.is_email_verified is True


def test_verify_email_already_verified():
    user = UserFactory()  # already verified
    token = make_email_verification_token(user)
    with pytest.raises(EmailAlreadyVerifiedError):
        verify_email(token=token)


def test_verify_email_bad_token():
    with pytest.raises(InvalidTokenError):
        verify_email(token="not-a-real-token")


# --- password reset ---------------------------------------------------------
def test_confirm_password_reset_success():
    user = UserFactory()
    uidb64, token = make_password_reset_token(user)
    confirm_password_reset(uidb64=uidb64, token=token, new_password="BrandNew123!")
    user.refresh_from_db()
    assert user.check_password("BrandNew123!")


def test_confirm_password_reset_token_is_one_time_use():
    user = UserFactory()
    uidb64, token = make_password_reset_token(user)
    confirm_password_reset(uidb64=uidb64, token=token, new_password="BrandNew123!")
    # Re-using the same token after the password changed must fail.
    with pytest.raises(InvalidTokenError):
        confirm_password_reset(uidb64=uidb64, token=token, new_password="Another123!")


def test_confirm_password_reset_bad_token():
    user = UserFactory()
    uidb64, _ = make_password_reset_token(user)
    with pytest.raises(InvalidTokenError):
        confirm_password_reset(uidb64=uidb64, token="bad-token", new_password="BrandNew123!")


# --- change password --------------------------------------------------------
def test_change_password_success():
    user = UserFactory()
    change_password(
        user=user,
        current_password=DEFAULT_PASSWORD,
        new_password="Changed123!",
    )
    user.refresh_from_db()
    assert user.check_password("Changed123!")


def test_change_password_wrong_current():
    user = UserFactory()
    with pytest.raises(IncorrectPasswordError):
        change_password(user=user, current_password="Nope123!", new_password="Changed123!")


# --- update profile ---------------------------------------------------------
def test_update_profile_updates_whitelisted_fields():
    user = UserFactory(first_name="Old")
    update_profile(user=user, first_name="New", is_staff=True)
    user.refresh_from_db()
    assert user.first_name == "New"
    assert user.is_staff is False  # is_staff is not whitelisted
