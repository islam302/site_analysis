"""Tests for users Celery tasks (run eagerly in the test settings)."""
import pytest
from django.core import mail

from apps.users.tasks import send_password_reset_email, send_verification_email
from apps.users.tests.factories import UnverifiedUserFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_send_verification_email_sends_message():
    user = UnverifiedUserFactory()
    send_verification_email(user_id=str(user.id))
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to
    assert "verify-email?token=" in mail.outbox[0].body


def test_send_verification_email_missing_user_is_noop():
    import uuid

    send_verification_email(user_id=str(uuid.uuid4()))
    assert len(mail.outbox) == 0


def test_send_password_reset_email_sends_message():
    user = UserFactory()
    send_password_reset_email(user_id=str(user.id))
    assert len(mail.outbox) == 1
    assert "reset-password?uid=" in mail.outbox[0].body
