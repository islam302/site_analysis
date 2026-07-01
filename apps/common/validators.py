"""Reusable field validators."""
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _

# Only allow http(s) URLs for analysis targets.
_http_url_validator = URLValidator(schemes=["http", "https"])


def validate_http_url(value: str) -> None:
    """Validate that ``value`` is a well-formed http(s) URL."""
    _http_url_validator(value)


def validate_no_localhost(value: str) -> None:
    """Reject obvious SSRF targets (localhost / private-ish hostnames).

    A lightweight guard for user-submitted URLs; deeper validation belongs to
    whatever performs the actual outbound request.
    """
    lowered = value.lower()
    blocked = ("localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.")
    if any(token in lowered for token in blocked):
        raise ValidationError(_("Local and link-local addresses are not allowed."))


def validate_file_size(max_mb: int):
    """Return a validator that rejects files larger than ``max_mb`` megabytes."""

    def _validate(file) -> None:
        limit = max_mb * 1024 * 1024
        if file.size > limit:
            raise ValidationError(_("File too large. Maximum size is %(mb)d MB.") % {"mb": max_mb})

    return _validate
