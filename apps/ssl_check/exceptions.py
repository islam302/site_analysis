"""Domain exceptions for the ssl_check app."""
from rest_framework import status

from apps.common.exceptions import ApplicationError


class SSLReportNotFoundError(ApplicationError):
    default_message = "SSL report not found."
    default_status = status.HTTP_404_NOT_FOUND


class SSLScanError(ApplicationError):
    """The TLS scan could not be completed (DNS/connection failure, etc.)."""

    default_message = "The SSL/TLS scan could not be completed."
    default_status = status.HTTP_502_BAD_GATEWAY
