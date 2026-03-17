"""Authentication URL configuration."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .two_factor import (
    TwoFactorEnrollView, TwoFactorVerifyView, TwoFactorDisableView, TwoFactorStatusView,
)

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('profile/', views.ProfileView.as_view(), name='auth-profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    # Password reset (unauthenticated)
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='auth-reset-password'),
    # Invite
    path('invite/', views.InviteUserView.as_view(), name='auth-invite'),
    path('invite-accept/', views.InviteAcceptView.as_view(), name='auth-invite-accept'),
    # 2FA (TOTP)
    path('2fa/status/', TwoFactorStatusView.as_view(), name='2fa-status'),
    path('2fa/enroll/', TwoFactorEnrollView.as_view(), name='2fa-enroll'),
    path('2fa/verify/', TwoFactorVerifyView.as_view(), name='2fa-verify'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='2fa-disable'),
]
