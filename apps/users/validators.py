"""Password complexity validator wired into AUTH_PASSWORD_VALIDATORS."""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_SPECIAL = re.compile(r"[^\w\s]")


class PasswordComplexityValidator:
    """Enforce at least one upper, lower, digit, and special character.

    Length is handled separately by Django's ``MinimumLengthValidator`` (>= 8).
    """

    def validate(self, password: str, user=None) -> None:
        errors = []
        if not _UPPER.search(password):
            errors.append(_("at least one uppercase letter"))
        if not _LOWER.search(password):
            errors.append(_("at least one lowercase letter"))
        if not _DIGIT.search(password):
            errors.append(_("at least one digit"))
        if not _SPECIAL.search(password):
            errors.append(_("at least one special character"))
        if errors:
            raise ValidationError(
                _("Password must contain %(reqs)s.") % {"reqs": ", ".join(errors)},
                code="password_too_weak",
            )

    def get_help_text(self) -> str:
        return _(
            "Your password must contain at least one uppercase letter, one "
            "lowercase letter, one digit, and one special character."
        )
