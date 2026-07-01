"""Header-based API key authentication.

Clients may authenticate by sending their key in the ``X-API-Key`` header
instead of a JWT. This runs after JWT in ``DEFAULT_AUTHENTICATION_CLASSES``.
"""
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.users.models import ApiKey

API_KEY_HEADER = "HTTP_X_API_KEY"


class ApiKeyAuthentication(BaseAuthentication):
    """Authenticate a request from an ``X-API-Key`` header."""

    def authenticate(self, request):
        key = request.META.get(API_KEY_HEADER)
        if not key:
            return None  # Fall through to other authenticators.

        try:
            api_key = ApiKey.objects.select_related("user").get(key=key, is_active=True)
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key.")

        if not api_key.user.is_active:
            raise AuthenticationFailed("User account is inactive.")

        # Best-effort usage timestamp; avoid touching updated_at churn elsewhere.
        ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        return (api_key.user, api_key)

    def authenticate_header(self, request) -> str:
        return "X-API-Key"
