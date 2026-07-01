"""Current-user profile endpoint."""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import UpdateProfileSerializer, UserSerializer
from apps.users.services import update_profile


class CurrentUserView(APIView):
    """GET / PATCH the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer}, summary="Get the current user")
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UpdateProfileSerializer,
        responses={200: UserSerializer},
        summary="Update the current user's profile",
    )
    def patch(self, request: Request) -> Response:
        serializer = UpdateProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = update_profile(user=request.user, **serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
