"""Celery tasks for the users app.

Tasks take primitive arguments (a stringified user id), are idempotent, and
retry transient mail-server failures with exponential backoff.
"""
from __future__ import annotations

import logging
import smtplib

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.users.tokens import make_email_verification_token, make_password_reset_token

logger = logging.getLogger("apps.users")
User = get_user_model()

_RETRY_KWARGS = dict(
    autoretry_for=(smtplib.SMTPException, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
)


def _send_html_email(*, subject: str, template: str, context: dict, to: str) -> None:
    html_body = render_to_string(template, context)
    text_body = strip_tags(html_body)
    send_mail(
        subject=subject,
        message=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        html_message=html_body,
        fail_silently=False,
    )


@shared_task(bind=True, **_RETRY_KWARGS)
def send_verification_email(self, user_id: str) -> None:
    """Email an email-verification link to the user."""
    logger.info("Sending verification email", extra={"user_id": user_id})
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning("Verification email skipped; user missing", extra={"user_id": user_id})
        return

    token = make_email_verification_token(user)
    link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
    _send_html_email(
        subject="Verify your email address",
        template="emails/verify_email.html",
        context={"user": user, "verification_url": link},
        to=user.email,
    )
    logger.info("Verification email sent", extra={"user_id": user_id})


@shared_task(bind=True, **_RETRY_KWARGS)
def send_password_reset_email(self, user_id: str) -> None:
    """Email a password-reset link to the user."""
    logger.info("Sending password reset email", extra={"user_id": user_id})
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning("Reset email skipped; user missing", extra={"user_id": user_id})
        return

    uidb64, token = make_password_reset_token(user)
    link = f"{settings.FRONTEND_BASE_URL}/reset-password?uid={uidb64}&token={token}"
    _send_html_email(
        subject="Reset your password",
        template="emails/password_reset.html",
        context={"user": user, "reset_url": link},
        to=user.email,
    )
    logger.info("Password reset email sent", extra={"user_id": user_id})
