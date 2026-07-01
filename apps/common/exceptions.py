"""Global exception handling.

Defines a single application-level exception type and a DRF exception handler
that turns every error into the project's standard error envelope:

    {"error": "<message>", "extra": {...}}
"""
import logging

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.common")


class ApplicationError(Exception):
    """Base class for all domain/business errors raised by services.

    Services raise subclasses of this instead of DRF/Django exceptions so the
    business layer stays framework-agnostic. The handler below renders them.
    """

    default_message = "An application error occurred."
    default_status = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        message: str | None = None,
        *,
        extra: dict | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.extra = extra or {}
        self.status_code = status_code or self.default_status
        super().__init__(self.message)


def custom_exception_handler(exc, context) -> Response | None:
    """Render every exception as the standard error envelope.

    Order of handling:
    1. Domain ``ApplicationError`` -> its own status + extra payload.
    2. Anything DRF understands -> normalized into the envelope.
    3. Everything else -> logged with traceback, generic 500.
    """
    request = context.get("request")
    request_id = getattr(request, "correlation_id", None)
    log_extra = {"request_id": request_id, "path": getattr(request, "path", None)}

    if isinstance(exc, ApplicationError):
        logger.warning("ApplicationError: %s", exc.message, extra={**log_extra, **exc.extra})
        return Response(
            {"error": exc.message, "extra": exc.extra},
            status=exc.status_code,
        )

    if isinstance(exc, Http404):
        return Response({"error": "Not found.", "extra": {}}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, PermissionDenied):
        return Response(
            {"error": "Permission denied.", "extra": {}},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, IntegrityError):
        logger.warning("IntegrityError: %s", exc, extra=log_extra)
        return Response(
            {"error": "The operation conflicts with existing data.", "extra": {}},
            status=status.HTTP_409_CONFLICT,
        )

    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception", exc_info=exc, extra=log_extra)
        return Response(
            {"error": "An unexpected error occurred.", "extra": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        response.data = {"error": str(detail["detail"]), "extra": {}}
    else:
        response.data = {"error": "Validation failed.", "extra": detail}

    return response
