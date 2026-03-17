"""Accounts URL routing — auth, profile, sessions, 2FA, account management."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # Registration (#1–2, #31, #34)
    path("register/", views.RegisterView.as_view(), name="register"),
    path("register/phone/", views.PhoneRegisterView.as_view(), name="register-phone"),

    # Login (#3–8)
    path("login/", views.LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Phone OTP (#8)
    path("otp/verify/", views.PhoneOTPVerifyView.as_view(), name="otp-verify"),

    # Magic link (#7)
    path("magic-link/request/", views.MagicLinkRequestView.as_view(), name="magic-link-request"),
    path("magic-link/verify/", views.MagicLinkVerifyView.as_view(), name="magic-link-verify"),

    # Social OAuth (#3–6)
    path("social/google/", views.GoogleAuthView.as_view(), name="social-google"),
    path("social/facebook/", views.FacebookAuthView.as_view(), name="social-facebook"),
    path("social/linkedin/", views.LinkedInAuthView.as_view(), name="social-linkedin"),
    path("social/apple/", views.AppleAuthView.as_view(), name="social-apple"),

    # Social linking (#21–22)
    path("social/link/", views.SocialLinkView.as_view(), name="social-link"),
    path("social/unlink/", views.SocialUnlinkView.as_view(), name="social-unlink"),

    # Email verification (#19)
    path("email/verify/", views.EmailVerifyView.as_view(), name="email-verify"),
    path("email/resend/", views.ResendVerificationView.as_view(), name="email-resend"),
    path("email/change/", views.EmailChangeView.as_view(), name="email-change"),
    path("email/change/confirm/", views.EmailChangeConfirmView.as_view(), name="email-change-confirm"),

    # Phone change (#20)
    path("phone/change/", views.PhoneChangeView.as_view(), name="phone-change"),
    path("phone/change/confirm/", views.PhoneChangeConfirmView.as_view(), name="phone-change-confirm"),

    # Password (#12–13)
    path("password/reset/", views.PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("password/reset/sms/", views.PasswordResetSMSView.as_view(), name="password-reset-sms"),
    path("password/reset/sms/confirm/", views.PasswordResetSMSConfirmView.as_view(), name="password-reset-sms-confirm"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password-change"),

    # NIC Recovery (#26)
    path("recovery/nic/", views.NICRecoveryView.as_view(), name="nic-recovery"),

    # 2FA (#10)
    path("2fa/setup/", views.TwoFactorSetupView.as_view(), name="2fa-setup"),

    # Profile (#28–30)
    path("profile/", views.ProfileView.as_view(), name="profile"),

    # Role switching (#18)
    path("role/switch/", views.SwitchRoleView.as_view(), name="role-switch"),

    # Sessions (#16–17)
    path("sessions/", views.SessionListView.as_view(), name="session-list"),
    path("sessions/<int:pk>/revoke/", views.SessionRevokeView.as_view(), name="session-revoke"),
    path("sessions/<int:pk>/trust/", views.TrustDeviceView.as_view(), name="session-trust"),
    path("sessions/revoke-all/", views.SessionRevokeAllView.as_view(), name="session-revoke-all"),

    # Push tokens (#27)
    path("push-tokens/", views.PushTokenView.as_view(), name="push-tokens"),

    # ToS (#32)
    path("tos/accept/", views.AcceptTosView.as_view(), name="tos-accept"),

    # Account management (#14–15)
    path("deactivate/", views.DeactivateAccountView.as_view(), name="account-deactivate"),
    path("delete/", views.DeleteAccountView.as_view(), name="account-delete"),

    # Employer verification (#35)
    path("employer/verify/", views.EmployerVerificationView.as_view(), name="employer-verify"),
]
