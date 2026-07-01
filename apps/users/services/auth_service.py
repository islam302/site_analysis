"""Authentication & account business logic.

Views call these functions; they never touch the ORM or send email directly.
Every write is wrapped in a transaction, side effects (email) are dispatched to
Celery, and domain errors are raised as :class:`ApplicationError` subclasses.
"""
from __future__ import annotations

import logging

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import status

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
from apps.users.selectors import get_user_by_email
from apps.users.tasks import send_password_reset_email, send_verification_email
from apps.users.tokens import (
    check_password_reset_token,
    decode_uid,
    read_email_verification_token,
)

logger = logging.getLogger("apps.users")
User = get_user_model()


def _validate_password_strength(*, password: str, user=None) -> None:
    """Run Django's configured validators; re-raise as an ApplicationError."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ApplicationError(
            "Password does not meet the security requirements.",
            extra={"password": list(exc.messages)},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@transaction.atomic
def register_user(
    *,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> "User":
    """Create a new (unverified) user and dispatch a verification email."""
    email = User.objects.normalize_email(email)
    if get_user_by_email(email=email) is not None:
        raise EmailAlreadyRegisteredError(extra={"email": email})
    if User.objects.filter(username=username).exists():
        raise UsernameAlreadyTakenError(extra={"username": username})

    _validate_password_strength(password=password)

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=False,
        )
    except IntegrityError:
        # Race on the unique email/username constraints.
        if get_user_by_email(email=email) is not None:
            raise EmailAlreadyRegisteredError(extra={"email": email})
        raise UsernameAlreadyTakenError(extra={"username": username})

    logger.info(
        "User registered",
        extra={"user_id": str(user.id), "email": email, "username": username},
    )
    send_verification_email.delay(user_id=str(user.id))
    return user


def authenticate_user(*, email: str, password: str) -> "User":
    """Validate credentials and return the user."""
    email = User.objects.normalize_email(email)
    user = authenticate(username=email, password=password)
    if user is None:
        existing = get_user_by_email(email=email)
        if existing is not None and not existing.is_active:
            raise InactiveAccountError()
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveAccountError()

    logger.info("User authenticated", extra={"user_id": str(user.id)})
    return user


@transaction.atomic
def verify_email(*, token: str) -> "User":
    """Verify a user's email from a signed token."""
    user_id = read_email_verification_token(token)
    if user_id is None:
        raise InvalidTokenError()

    try:
        user = User.objects.select_for_update().get(id=user_id)
    except (User.DoesNotExist, ValueError):
        raise InvalidTokenError()

    if user.is_email_verified:
        raise EmailAlreadyVerifiedError()

    user.is_email_verified = True
    user.save(update_fields=["is_email_verified", "updated_at"])
    logger.info("Email verified", extra={"user_id": str(user.id)})
    return user


def resend_verification_email(*, email: str) -> None:
    """Re-dispatch a verification email if the account exists and is unverified."""
    user = get_user_by_email(email=email)
    if user is not None and user.is_active and not user.is_email_verified:
        send_verification_email.delay(user_id=str(user.id))
    logger.info("Verification resend requested", extra={"email": email})


def request_password_reset(*, email: str) -> None:
    """Dispatch a password-reset email if the account exists (no enumeration)."""
    user = get_user_by_email(email=email)
    if user is not None and user.is_active:
        send_password_reset_email.delay(user_id=str(user.id))
    logger.info("Password reset requested", extra={"email": email})


@transaction.atomic
def confirm_password_reset(*, uidb64: str, token: str, new_password: str) -> "User":
    """Set a new password from a valid, one-time-use reset token."""
    user_id = decode_uid(uidb64)
    if user_id is None:
        raise InvalidTokenError()

    try:
        user = User.objects.select_for_update().get(id=user_id)
    except (User.DoesNotExist, ValueError):
        raise InvalidTokenError()

    if not check_password_reset_token(user, token):
        raise InvalidTokenError()

    _validate_password_strength(password=new_password, user=user)
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    logger.info("Password reset completed", extra={"user_id": str(user.id)})
    return user


@transaction.atomic
def change_password(*, user, current_password: str, new_password: str) -> "User":
    """Change an authenticated user's password after verifying the old one."""
    if not user.check_password(current_password):
        raise IncorrectPasswordError()

    _validate_password_strength(password=new_password, user=user)
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    logger.info("Password changed", extra={"user_id": str(user.id)})
    return user


@transaction.atomic
def update_profile(*, user, **fields) -> "User":
    """Update mutable profile fields (first_name, last_name)."""
    allowed = {"first_name", "last_name"}
    update_fields: list[str] = []
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(user, key, value)
            update_fields.append(key)

    if update_fields:
        update_fields.append("updated_at")
        user.save(update_fields=update_fields)
        logger.info(
            "Profile updated",
            extra={"user_id": str(user.id), "fields": update_fields},
        )
    return user
