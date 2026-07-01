"""Domain exceptions for the analysis app."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class ReportNotFoundError(ApplicationError):
    default_message = "Analysis report not found."
    default_status = status.HTTP_404_NOT_FOUND


class PageSpeedAPIError(ApplicationError):
    """Raised when the upstream PageSpeed Insights API fails."""

    default_message = "The PageSpeed Insights API request failed."
    default_status = status.HTTP_502_BAD_GATEWAY


class PageSpeedConfigError(ApplicationError):
    """Raised when the PageSpeed API key is not configured."""

    default_message = "PageSpeed Insights API key is not configured."
    default_status = status.HTTP_503_SERVICE_UNAVAILABLE
