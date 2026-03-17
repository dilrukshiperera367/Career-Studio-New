from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.two_factor import (
    TwoFactorEnrollView, TwoFactorVerifyView, TwoFactorDisableView, TwoFactorStatusView,
)
from apps.accounts.views import (
    RegisterView, LoginView, MeView, UserListView,
    CompanyRegisterView, CandidateRegisterView,
    ChangePasswordView, ForgotPasswordView, ResetPasswordView,
    InviteUserView, InviteAcceptView, UserDeactivateView,
    InviteManagementView, InviteCancelView, InviteResendView,
    MFAEnableView, MFAVerifyView, MFADisableView,
    LogoutView,
    UserPermissionsView,
    EmailVerificationSendView, EmailVerificationConfirmView,
)

urlpatterns = [
    # New split registration
    path("register/company/", CompanyRegisterView.as_view(), name="auth-register-company"),
    path("register/candidate/", CandidateRegisterView.as_view(), name="auth-register-candidate"),
    # Legacy
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    # Password reset (unauthenticated)
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    # Team invite
    path("invite/", InviteUserView.as_view(), name="auth-invite"),
    path("invite-accept/", InviteAcceptView.as_view(), name="auth-invite-accept"),
    # Invitation management (#52) — list pending, cancel, resend
    path("invites/", InviteManagementView.as_view(), name="auth-invites-list"),
    path("invites/<uuid:invite_id>/", InviteCancelView.as_view(), name="auth-invite-cancel"),
    path("invites/<uuid:invite_id>/resend/", InviteResendView.as_view(), name="auth-invite-resend"),
    # User management
    path("users/", UserListView.as_view(), name="auth-users"),
    path("users/<uuid:user_id>/deactivate/", UserDeactivateView.as_view(), name="auth-user-deactivate"),
    # MFA (TOTP)
    path("mfa/enable/", MFAEnableView.as_view(), name="auth-mfa-enable"),
    path("mfa/verify/", MFAVerifyView.as_view(), name="auth-mfa-verify"),
    path("mfa/disable/", MFADisableView.as_view(), name="auth-mfa-disable"),
    # 2FA (TOTP — extended)
    path("2fa/status/", TwoFactorStatusView.as_view(), name="2fa-status"),
    path("2fa/enroll/", TwoFactorEnrollView.as_view(), name="2fa-enroll"),
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="2fa-verify"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa-disable"),
    # Permissions audit
    path("me/permissions/", UserPermissionsView.as_view(), name="user-permissions"),
    # Email verification (#17)
    path("email/verify/send/", EmailVerificationSendView.as_view(), name="email-verify-send"),
    path("email/verify/confirm/", EmailVerificationConfirmView.as_view(), name="email-verify-confirm"),
]
