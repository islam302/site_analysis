"""Permission classes for the users app."""
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.users.constants import UserRole


class IsAdminRole(BasePermission):
    """Allow only users with the ``admin`` role (or Django superusers)."""

    message = "Administrator access required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role == UserRole.ADMIN or user.is_superuser)
        )
