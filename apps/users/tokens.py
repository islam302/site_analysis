"""Stateless tokens for email verification and password reset.

- **Email verification** uses a :class:`~django.core.signing.TimestampSigner`
  signing the user id under a dedicated salt, with a configurable max age.
- **Password reset** uses Django's :data:`default_token_generator`, which ties
  validity to the user's password hash and last-login timestamp — making each
  token implicitly one-time-use (it is invalidated the moment the password
  changes) and time-limited via ``PASSWORD_RESET_TIMEOUT``.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.users.constants import EMAIL_VERIFICATION_SALT


def make_email_verification_token(user) -> str:
    """Return a signed, time-limited email-verification token for ``user``."""
    return signing.dumps(str(user.id), salt=EMAIL_VERIFICATION_SALT)


def read_email_verification_token(token: str) -> str | None:
    """Return the user id encoded in ``token`` or ``None`` if invalid/expired."""
    try:
        return signing.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=settings.EMAIL_VERIFICATION_TIMEOUT,
        )
    except signing.BadSignature:
        return None


def make_password_reset_token(user) -> tuple[str, str]:
    """Return ``(uidb64, token)`` for a password-reset link."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.id))
    token = default_token_generator.make_token(user)
    return uidb64, token


def decode_uid(uidb64: str) -> str | None:
    """Decode a base64-encoded user id, or ``None`` if malformed."""
    try:
        return force_str(urlsafe_base64_decode(uidb64))
    except (TypeError, ValueError, OverflowError):
        return None


def check_password_reset_token(user, token: str) -> bool:
    """Validate a password-reset ``token`` against ``user``."""
    return default_token_generator.check_token(user, token)
