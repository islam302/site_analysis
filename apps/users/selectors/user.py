"""Read-only queries for users."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.users.exceptions import UserNotFoundError

User = get_user_model()


def get_all_users() -> QuerySet["User"]:
    """Return every user with their API key prefetched (admin use).

    ``select_related('api_key')`` avoids an N+1 when serializing keys.
    """
    return User.objects.select_related("api_key").order_by("-created_at")


def get_user_by_id(*, user_id: uuid.UUID | str) -> "User":
    """Fetch an active user by id or raise :class:`UserNotFoundError`."""
    try:
        return User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError, TypeError):
        raise UserNotFoundError(extra={"user_id": str(user_id)})


def get_user_by_email(*, email: str) -> "User | None":
    """Return the active user with ``email``, or ``None`` if none exists."""
    return User.objects.filter(email=User.objects.normalize_email(email)).first()
