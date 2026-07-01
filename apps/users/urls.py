"""Auth & user routes, mounted under /api/v1/auth/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    AdminUserViewSet,
    ChangePasswordView,
    CurrentUserView,
    EmailVerificationResendView,
    EmailVerificationView,
    LoginView,
    LogoutView,
    MyApiKeyView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)

app_name = "users"

router = DefaultRouter()
router.register("admin/users", AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("email/verify/", EmailVerificationView.as_view(), name="email-verify"),
    path(
        "email/verify/resend/",
        EmailVerificationResendView.as_view(),
        name="email-verify-resend",
    ),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("me/api-key/", MyApiKeyView.as_view(), name="my-api-key"),
    path("", include(router.urls)),
]
