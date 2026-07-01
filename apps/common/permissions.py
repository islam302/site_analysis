"""Shared permission classes."""
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsEmailVerified(BasePermission):
    """Allow access only to authenticated users with a verified email.

    Per project policy, unverified users may authenticate (obtain tokens) but
    cannot reach protected business resources.
    """

    message = "Email address must be verified to access this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_email_verified)


class IsOwner(BasePermission):
    """Object-level permission: the object's ``user`` must be the requester."""

    message = "You do not have permission to access this object."

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        owner = getattr(obj, "user", None)
        return owner is not None and owner == request.user


class IsOwnerOrReadOnly(BasePermission):
    """Read for anyone authenticated; write only for the owner."""

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, "user", None) == request.user
