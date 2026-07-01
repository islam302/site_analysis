"""Custom user model.

Combines Django's auth mixins with the project :class:`BaseModel` so users get
a UUID primary key, audit timestamps, and soft-delete support. Email is the
login identifier; usernames are not used.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.users.constants import UserRole
from apps.users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        db_index=True,
        validators=[UnicodeUsernameValidator()],
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
    )
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        db_index=True,
    )

    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Inactive accounts cannot authenticate."),
    )
    is_staff = models.BooleanField(_("staff status"), default=False)
    is_email_verified = models.BooleanField(_("email verified"), default=False)

    objects = UserManager()

    # Login is still by email; username is an additional required identifier.
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"], name="user_email_idx"),
            models.Index(fields=["username"], name="user_username_idx"),
            models.Index(fields=["role"], name="user_role_idx"),
            models.Index(fields=["is_active", "is_email_verified"], name="user_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(is_deleted=False),
                name="unique_active_user_email",
            ),
        ]

    def __str__(self) -> str:
        return self.username

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.first_name
