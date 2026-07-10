"""Domain exceptions for the GTmetrix app."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class GTmetrixReportNotFoundError(ApplicationError):
    default_message = "GTmetrix report not found."
    default_status = status.HTTP_404_NOT_FOUND


class GTmetrixAPIError(ApplicationError):
    """Retryable upstream failure (network, 5xx, or the test errored out)."""

    default_message = "The GTmetrix API request failed."
    default_status = status.HTTP_502_BAD_GATEWAY


class GTmetrixClientError(ApplicationError):
    """Non-retryable 4xx from GTmetrix (bad request, out of credits, etc.).

    Deliberately NOT a subclass of :class:`GTmetrixAPIError` so the Celery task
    does not retry it — retrying a client error just fails again.
    """

    default_message = "GTmetrix rejected the request."
    default_status = status.HTTP_400_BAD_REQUEST


class GTmetrixConfigError(ApplicationError):
    default_message = "GTmetrix API key is not configured."
    default_status = status.HTTP_503_SERVICE_UNAVAILABLE


class GTmetrixTimeoutError(ApplicationError):
    default_message = "The GTmetrix test did not finish in time."
    default_status = status.HTTP_504_GATEWAY_TIMEOUT
