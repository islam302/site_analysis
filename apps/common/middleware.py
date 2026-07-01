"""Cross-cutting HTTP middleware: correlation IDs and structured request logging."""
import logging
import time
import uuid

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("apps.common")

CORRELATION_HEADER = "HTTP_X_REQUEST_ID"
CORRELATION_RESPONSE_HEADER = "X-Request-ID"


class CorrelationIdMiddleware:
    """Attach a correlation id to every request and echo it on the response.

    Honours an inbound ``X-Request-ID`` header if present (so a gateway/edge
    can propagate one), otherwise generates a UUID. Downstream code reads
    ``request.correlation_id`` and log records include it.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.META.get(CORRELATION_HEADER) or uuid.uuid4().hex
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response[CORRELATION_RESPONSE_HEADER] = correlation_id
        return response


class RequestLoggingMiddleware:
    """Emit one structured log line per request with timing and status."""

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        user = getattr(request, "user", None)
        user_id = str(user.id) if user is not None and user.is_authenticated else None

        logger.info(
            "request",
            extra={
                "request_id": getattr(request, "correlation_id", None),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
            },
        )
        return response
