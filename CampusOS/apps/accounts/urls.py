"""CampusOS — Accounts URLs."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    CampusTokenObtainView,
    ChangePasswordView,
    ConfirmPasswordResetView,
    MeView,
    RegisterView,
    RequestPasswordResetView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", CampusTokenObtainView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="auth-token-verify"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("password-reset/request/", RequestPasswordResetView.as_view(), name="auth-password-reset-request"),
    path("password-reset/confirm/", ConfirmPasswordResetView.as_view(), name="auth-password-reset-confirm"),
]
