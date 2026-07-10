"""API key views: a user's own key, plus admin-only user/key listing."""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminRole
from apps.users.selectors import get_all_users
from apps.users.serializers import AdminUserSerializer, ApiKeySerializer
from apps.users.services.api_key_service import get_or_create_api_key, rotate_api_key
from apps.common.pagination import DefaultPagination

logger = logging.getLogger("apps.users")


class MyApiKeyView(APIView):
    """GET the current user's API key; POST to rotate it."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: ApiKeySerializer}, summary="Get my API key")
    def get(self, request: Request) -> Response:
        api_key = get_or_create_api_key(user=request.user)
        return Response(ApiKeySerializer(api_key).data, status=status.HTTP_200_OK)

    @extend_schema(request=None, responses={200: ApiKeySerializer}, summary="Rotate my API key")
    def post(self, request: Request) -> Response:
        api_key = rotate_api_key(user=request.user)
        return Response(ApiKeySerializer(api_key).data, status=status.HTTP_200_OK)


class AdminUserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Admin-only: list/retrieve all users together with their API keys."""

    permission_classes = [IsAdminRole]
    serializer_class = AdminUserSerializer
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["role", "is_active", "is_email_verified"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["created_at", "username", "email", "role"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return get_all_users()
