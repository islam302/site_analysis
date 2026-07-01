"""Custom user manager.

Inherits the soft-delete-aware :class:`BaseManager` so the default queryset
hides soft-deleted users, while adding the create helpers that
``AbstractBaseUser`` requires.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import make_password

from apps.common.models import BaseManager
from apps.users.constants import UserRole

if TYPE_CHECKING:
    from apps.users.models import User


class UserManager(BaseManager, BaseUserManager):
    """Manager exposing ``create_user`` / ``create_superuser``.

    Inherits :class:`BaseManager` (so the default queryset hides soft-deleted
    rows) and Django's :class:`BaseUserManager` (for ``get_by_natural_key`` and
    ``normalize_email``, which the auth backend relies on). ``BaseManager`` is
    first in the MRO so its soft-delete ``get_queryset`` wins.
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> "User":
        if not email:
            raise ValueError("The email address must be set.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("role", UserRole.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)
