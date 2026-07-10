"""Domain exceptions for the audits app."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class AuditNotFoundError(ApplicationError):
    default_message = "Accessibility audit not found."
    default_status = status.HTTP_404_NOT_FOUND


class WaveAPIError(ApplicationError):
    """Raised when the WAVE API request fails or returns an unsuccessful status."""

    default_message = "The WAVE accessibility API request failed."
    default_status = status.HTTP_502_BAD_GATEWAY


class WaveConfigError(ApplicationError):
    default_message = "WAVE API key is not configured."
    default_status = status.HTTP_503_SERVICE_UNAVAILABLE
