"""Thin auth views.

Each view: validates input via a serializer, calls an auth service, returns a
serialized response. No business logic lives here. Sensitive endpoints apply
the 5/min ``AuthRateThrottle``.
"""
import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.throttling import AuthRateThrottle
from apps.users.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from apps.users.services import (
    change_password,
    confirm_password_reset,
    register_user,
    request_password_reset,
    resend_verification_email,
    verify_email,
)
from apps.users.services.auth_service import authenticate_user

logger = logging.getLogger("apps.users")


def _tokens_for_user(user) -> dict[str, str]:
    """Issue an access/refresh token pair for ``user``."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserSerializer},
        summary="Register a new user",
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = register_user(**serializer.validated_data)

        tokens = _tokens_for_user(user)
        return Response(
            {"user": UserSerializer(user).data, **tokens},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={200: OpenApiResponse(description="access, refresh, and user")},
        summary="Obtain JWT access & refresh tokens",
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate_user(**serializer.validated_data)

        tokens = _tokens_for_user(user)
        return Response(
            {"user": UserSerializer(user).data, **tokens},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={205: OpenApiResponse(description="Refresh token blacklisted")},
        summary="Blacklist a refresh token (logout)",
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                {"error": "Invalid or expired refresh token.", "extra": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("User logged out", extra={"user_id": str(request.user.id)})
        return Response(status=status.HTTP_205_RESET_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed")},
        summary="Change the current user's password",
    )
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        change_password(user=request.user, **serializer.validated_data)
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Reset email dispatched if account exists")},
        summary="Request a password reset email",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_password_reset(**serializer.validated_data)
        # Always 200 — never reveal whether the email is registered.
        return Response(
            {"detail": "If an account exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password reset")},
        summary="Confirm a password reset with token",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        confirm_password_reset(
            uidb64=data["uid"],
            token=data["token"],
            new_password=data["new_password"],
        )
        return Response({"detail": "Password has been reset."}, status=status.HTTP_200_OK)


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyEmailSerializer,
        responses={200: OpenApiResponse(description="Email verified")},
        summary="Verify an email address with a token",
    )
    def post(self, request: Request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = verify_email(**serializer.validated_data)
        return Response(
            {"detail": "Email verified.", "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class EmailVerificationResendView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        request=ResendVerificationSerializer,
        responses={200: OpenApiResponse(description="Verification email dispatched if applicable")},
        summary="Resend the email verification message",
    )
    def post(self, request: Request) -> Response:
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resend_verification_email(**serializer.validated_data)
        return Response(
            {"detail": "If the account requires verification, an email has been sent."},
            status=status.HTTP_200_OK,
        )
