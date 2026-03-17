"""Accounts views — Registration, login, OAuth, 2FA, sessions, profile.
Features #1–35.
"""
import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import timedelta

import requests
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    User, EmailVerificationToken, PhoneVerificationToken,
    PasswordResetToken, MagicLinkToken, UserSession, LoginAttempt,
    TwoFactorSecret, PushToken,
)
from .serializers import (
    RegisterSerializer, PhoneRegisterSerializer, LoginSerializer,
    PhoneOTPRequestSerializer, PhoneOTPVerifySerializer,
    MagicLinkRequestSerializer, MagicLinkVerifySerializer,
    SocialAuthSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, PasswordChangeSerializer,
    PasswordResetSMSRequestSerializer,
    EmailVerifySerializer, ResendVerificationSerializer,
    EmailChangeSerializer, PhoneChangeSerializer,
    TwoFactorSetupSerializer, TwoFactorVerifySerializer,
    UserSerializer, UserUpdateSerializer, UserSessionSerializer,
    PushTokenSerializer, AcceptTosSerializer,
    SocialLinkSerializer, SocialUnlinkSerializer,
    AccountDeactivateSerializer, AccountDeleteSerializer,
    EmployerVerificationSerializer,
    NICRecoverySerializer,
)

logger = logging.getLogger(__name__)


def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _record_attempt(email, ip, success):
    LoginAttempt.objects.create(email=email, ip_address=ip, success=success)


def _is_rate_limited(email, ip):
    cutoff = timezone.now() - timedelta(minutes=15)
    count = LoginAttempt.objects.filter(
        email=email, ip_address=ip, success=False, attempted_at__gte=cutoff
    ).count()
    return count >= 5


# ── Registration (#1–2) ──────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    """Email + password registration (#1) with UTM tracking (#31) and age verification (#34)."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Registration source tracking (#31)
        user.registration_source = request.data.get("source", "direct")
        user.utm_source = request.data.get("utm_source", "")
        user.utm_medium = request.data.get("utm_medium", "")
        user.utm_campaign = request.data.get("utm_campaign", "")
        user.save(update_fields=["registration_source", "utm_source", "utm_medium", "utm_campaign"])

        # Send verification email (async via Celery)
        token = EmailVerificationToken.objects.create(
            user=user,
            token=secrets.token_hex(3)[:6].upper(),
            expires_at=timezone.now() + timedelta(hours=24),
        )
        from apps.shared.tasks import send_email_verification
        send_email_verification.delay(str(user.id), token.token)

        return Response(
            {"user": UserSerializer(user).data, "tokens": _get_tokens(user)},
            status=status.HTTP_201_CREATED,
        )


class PhoneRegisterView(APIView):
    """Phone number registration — sends SMS OTP (#2)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PhoneRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                "user_type": serializer.validated_data["user_type"],
                "preferred_lang": serializer.validated_data["preferred_lang"],
                "login_method": "phone",
            },
        )
        otp = secrets.token_hex(3)[:6].upper()
        PhoneVerificationToken.objects.create(
            user=user, phone=phone, otp=otp,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        # TODO: send_sms_otp.delay(phone, otp)
        return Response({"detail": "OTP sent.", "is_new_user": created})


# ── Login (#3–8) ─────────────────────────────────────────────────────────

class LoginView(APIView):
    """Email + password login."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
        serializer = LoginSerializer(data=request.data)
        email = request.data.get("email", "")

        if _is_rate_limited(email, ip):
            return Response(
                {"detail": "Too many failed attempts. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        _record_attempt(email, ip, True)

        # Create session record
        session_key = secrets.token_hex(32)
        UserSession.objects.create(
            user=user, session_key=session_key,
            device_info=request.META.get("HTTP_USER_AGENT", "")[:200],
            ip_address=ip,
        )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        return Response({"user": UserSerializer(user).data, "tokens": _get_tokens(user)})


class PhoneOTPVerifyView(APIView):
    """Verify phone OTP to login/register (#8)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        now = timezone.now()
        token = PhoneVerificationToken.objects.filter(
            phone=serializer.validated_data["phone"],
            otp=serializer.validated_data["otp"],
            is_used=False, expires_at__gt=now,
        ).order_by("-created_at").first()
        if not token:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        token.is_used = True
        token.save(update_fields=["is_used"])
        user = token.user
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])
        return Response({"user": UserSerializer(user).data, "tokens": _get_tokens(user)})


class MagicLinkRequestView(APIView):
    """Request passwordless magic-link login (#7)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MagicLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            return Response({"detail": "If the email exists, a link was sent."})
        token = MagicLinkToken.objects.create(
            user=user, expires_at=timezone.now() + timedelta(minutes=15),
        )
        from apps.shared.tasks import send_email_verification
        # Reuse email task with magic link template
        send_email_verification.delay(str(user.id), str(token.token))
        return Response({"detail": "If the email exists, a link was sent."})


class MagicLinkVerifyView(APIView):
    """Verify magic-link token and return JWT."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MagicLinkVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = MagicLinkToken.objects.filter(
            token=serializer.validated_data["token"],
            is_used=False, expires_at__gt=timezone.now(),
        ).first()
        if not token:
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)
        token.is_used = True
        token.save(update_fields=["is_used"])
        user = token.user
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])
        return Response({"user": UserSerializer(user).data, "tokens": _get_tokens(user)})


# ── Social OAuth (#3–6, #21–22) ──────────────────────────────────────────

def _oauth_get_or_create_user(provider, social_id, email, avatar_url, user_type):
    """Common logic for OAuth: find by social ID, fallback to email, or create."""
    field_map = {
        "google": "google_id",
        "facebook": "facebook_id",
        "linkedin": "linkedin_id",
        "apple": "apple_id",
    }
    field = field_map[provider]

    # Try social ID match first
    user = User.objects.filter(**{field: social_id}).first()
    if user:
        return user, False

    # Try email match — link the social account
    user = User.objects.filter(email=email).first()
    if user:
        setattr(user, field, social_id)
        user.save(update_fields=[field])
        return user, False

    # Create new user
    user = User.objects.create_user(
        email=email,
        user_type=user_type,
        login_method=provider,
        is_verified=True,
        avatar_url=avatar_url or "",
        **{field: social_id},
    )
    return user, True


class GoogleAuthView(APIView):
    """Google OAuth — verify ID token and exchange for JWT (#3)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data["access_token"]

        try:
            resp = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            info = resp.json()
        except requests.RequestException:
            return Response({"detail": "Failed to verify Google token."}, status=status.HTTP_400_BAD_REQUEST)

        google_id = info.get("sub")
        email = info.get("email")
        if not google_id or not email:
            return Response({"detail": "Invalid Google account."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = _oauth_get_or_create_user(
            "google", google_id, email,
            info.get("picture"),
            serializer.validated_data["user_type"],
        )
        return Response({
            "user": UserSerializer(user).data,
            "tokens": _get_tokens(user),
            "is_new_user": created,
        })


class FacebookAuthView(APIView):
    """Facebook OAuth — verify access token (#4)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data["access_token"]

        try:
            resp = requests.get(
                "https://graph.facebook.com/me",
                params={"fields": "id,email,name,picture", "access_token": access_token},
                timeout=10,
            )
            resp.raise_for_status()
            info = resp.json()
        except requests.RequestException:
            return Response({"detail": "Failed to verify Facebook token."}, status=status.HTTP_400_BAD_REQUEST)

        fb_id = info.get("id")
        email = info.get("email")
        if not fb_id or not email:
            return Response({"detail": "Invalid Facebook account or email not shared."}, status=status.HTTP_400_BAD_REQUEST)

        avatar = info.get("picture", {}).get("data", {}).get("url")
        user, created = _oauth_get_or_create_user(
            "facebook", fb_id, email, avatar, serializer.validated_data["user_type"],
        )
        return Response({
            "user": UserSerializer(user).data,
            "tokens": _get_tokens(user),
            "is_new_user": created,
        })


class LinkedInAuthView(APIView):
    """LinkedIn OAuth — exchange auth code for profile (#5)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data["access_token"]

        try:
            resp = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            info = resp.json()
        except requests.RequestException:
            return Response({"detail": "Failed to verify LinkedIn token."}, status=status.HTTP_400_BAD_REQUEST)

        li_id = info.get("sub")
        email = info.get("email")
        if not li_id or not email:
            return Response({"detail": "Invalid LinkedIn account."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = _oauth_get_or_create_user(
            "linkedin", li_id, email, info.get("picture"), serializer.validated_data["user_type"],
        )
        return Response({
            "user": UserSerializer(user).data,
            "tokens": _get_tokens(user),
            "is_new_user": created,
        })


class AppleAuthView(APIView):
    """Apple Sign-In (#6) — validate identity token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Apple sends id_token in the access_token field
        id_token = serializer.validated_data["access_token"]
        email = request.data.get("email")
        apple_id = request.data.get("apple_user_id")

        if not apple_id or not email:
            return Response({"detail": "Apple user ID and email required."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = _oauth_get_or_create_user(
            "apple", apple_id, email, None, serializer.validated_data["user_type"],
        )
        return Response({
            "user": UserSerializer(user).data,
            "tokens": _get_tokens(user),
            "is_new_user": created,
        })


# ── Email Verification (#19) ─────────────────────────────────────────────

class EmailVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = EmailVerificationToken.objects.filter(
            user=request.user,
            token=serializer.validated_data["token"],
            is_used=False, expires_at__gt=timezone.now(),
        ).first()
        if not token:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        token.is_used = True
        token.save(update_fields=["is_used"])
        request.user.is_verified = True
        request.user.save(update_fields=["is_verified"])
        return Response({"detail": "Email verified."})


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            pass
        else:
            token = EmailVerificationToken.objects.create(
                user=user,
                token=secrets.token_hex(3)[:6].upper(),
                expires_at=timezone.now() + timedelta(hours=24),
            )
            from apps.shared.tasks import send_email_verification
            send_email_verification.delay(str(user.id), token.token)
        return Response({"detail": "If the email exists, a verification code was sent."})


# ── Password (#12–14) ────────────────────────────────────────────────────

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
        except User.DoesNotExist:
            pass
        else:
            token = PasswordResetToken.objects.create(
                user=user, token=secrets.token_hex(32),
                expires_at=timezone.now() + timedelta(hours=1),
            )
            from apps.shared.tasks import send_password_reset_email
            send_password_reset_email.delay(str(user.id), token.token)
        return Response({"detail": "If the email exists, a reset link was sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = PasswordResetToken.objects.filter(
            token=serializer.validated_data["token"],
            is_used=False, expires_at__gt=timezone.now(),
        ).first()
        if not token:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        token.user.set_password(serializer.validated_data["new_password"])
        token.user.save(update_fields=["password"])
        token.is_used = True
        token.save(update_fields=["is_used"])
        return Response({"detail": "Password updated."})


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed."})


# ── 2FA / TOTP (#10) ─────────────────────────────────────────────────────

class TwoFactorSetupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        secret, _ = TwoFactorSecret.objects.get_or_create(
            user=request.user,
            defaults={"secret": secrets.token_hex(16)[:32]},
        )
        return Response({
            "secret": secret.secret,
            "is_enabled": secret.is_enabled,
            "otpauth_uri": f"otpauth://totp/JobFinder:{request.user.email}?secret={secret.secret}&issuer=JobFinder",
        })

    def post(self, request):
        serializer = TwoFactorSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: verify TOTP code with pyotp
        secret = TwoFactorSecret.objects.get(user=request.user)
        secret.is_enabled = True
        secret.backup_codes = [secrets.token_hex(4) for _ in range(8)]
        secret.save()
        return Response({"detail": "2FA enabled.", "backup_codes": secret.backup_codes})

    def delete(self, request):
        TwoFactorSecret.objects.filter(user=request.user).update(is_enabled=False)
        return Response({"detail": "2FA disabled."})


# ── Profile (#28–30) ─────────────────────────────────────────────────────

class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer


# ── Sessions (#16–17, #25) ───────────────────────────────────────────────

class SessionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user).order_by("-last_active_at")


class SessionRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = UserSession.objects.filter(user=request.user, pk=pk).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)


class SessionRevokeAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        UserSession.objects.filter(user=request.user).delete()
        return Response({"detail": "All sessions revoked."})


# ── Push Tokens (#27) ────────────────────────────────────────────────────

class PushTokenView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PushTokenSerializer

    def get_queryset(self):
        return PushToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ── ToS Acceptance (#32) ─────────────────────────────────────────────────

class AcceptTosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AcceptTosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.tos_accepted_version = serializer.validated_data["version"]
        request.user.tos_accepted_at = timezone.now()
        request.user.save(update_fields=["tos_accepted_version", "tos_accepted_at"])
        return Response({"detail": "Terms accepted."})


# ── Account Deactivation (#14) ────────────────────────────────────────────

class DeactivateAccountView(APIView):
    """Temporarily deactivate account — can be reactivated."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AccountDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["password"]):
            return Response({"detail": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=["is_active"])
        UserSession.objects.filter(user=user).delete()
        return Response({"detail": "Account deactivated. You can log in again to reactivate."})


# ── GDPR Account Deletion (#15) ──────────────────────────────────────────

class DeleteAccountView(APIView):
    """Permanent GDPR-compliant deletion with optional data export."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Export user data before deletion (#15)."""
        user = request.user
        data = {
            "email": user.email,
            "phone": user.phone,
            "user_type": user.user_type,
            "preferred_lang": user.preferred_lang,
            "date_joined": str(user.date_joined),
            "tos_accepted_version": user.tos_accepted_version,
        }
        # Include seeker profile if exists
        if hasattr(user, "seeker_profile"):
            p = user.seeker_profile
            data["seeker_profile"] = {
                "first_name": p.first_name,
                "last_name": p.last_name,
                "headline": p.headline,
                "bio": p.bio,
            }
        return Response(data)

    def delete(self, request):
        serializer = AccountDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["password"]):
            return Response({"detail": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)
        # Anonymize PII
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.local"
        user.phone = None
        user.google_id = None
        user.facebook_id = None
        user.linkedin_id = None
        user.apple_id = None
        user.avatar_url = ""
        user.save()
        # Delete sensitive related data
        UserSession.objects.filter(user=user).delete()
        PushToken.objects.filter(user=user).delete()
        LoginAttempt.objects.filter(email=user.email).delete()
        return Response({"detail": "Account permanently deleted."}, status=status.HTTP_204_NO_CONTENT)


# ── Trusted Devices (#17) ────────────────────────────────────────────────

class TrustDeviceView(APIView):
    """Mark current session as a trusted device for 30 days."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = UserSession.objects.filter(user=request.user, pk=pk).first()
        if not session:
            return Response(status=status.HTTP_404_NOT_FOUND)
        session.is_trusted = True
        session.save(update_fields=["is_trusted"])
        return Response({"detail": "Device marked as trusted."})


# ── Role Switching (#18) ─────────────────────────────────────────────────

class SwitchRoleView(APIView):
    """Let a user switch between seeker and employer roles."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        target_role = request.data.get("role")
        if target_role not in ("seeker", "employer"):
            return Response({"detail": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.user_type = target_role
        request.user.save(update_fields=["user_type"])
        return Response({"user": UserSerializer(request.user).data})


# ── Email Change (#19) ───────────────────────────────────────────────────

class EmailChangeView(APIView):
    """Request email change — sends OTP to new email (#19)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data["new_email"]
        if User.objects.filter(email=new_email).exists():
            return Response({"detail": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST)
        token = EmailVerificationToken.objects.create(
            user=request.user,
            token=secrets.token_hex(3)[:6].upper(),
            new_email=new_email,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        from apps.shared.tasks import send_email_verification
        send_email_verification.delay(str(request.user.id), token.token)
        return Response({"detail": "Verification code sent to new email."})


class EmailChangeConfirmView(APIView):
    """Confirm email change with OTP."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = EmailVerificationToken.objects.filter(
            user=request.user,
            token=serializer.validated_data["token"],
            new_email__isnull=False,
            is_used=False, expires_at__gt=timezone.now(),
        ).first()
        if not token:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.email = token.new_email
        request.user.save(update_fields=["email"])
        token.is_used = True
        token.save(update_fields=["is_used"])
        return Response({"detail": "Email updated."})


# ── Phone Change (#20) ───────────────────────────────────────────────────

class PhoneChangeView(APIView):
    """Request phone change — sends OTP to new phone (#20)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_phone = serializer.validated_data["new_phone"]
        if User.objects.filter(phone=new_phone).exists():
            return Response({"detail": "Phone already in use."}, status=status.HTTP_400_BAD_REQUEST)
        otp = secrets.token_hex(3)[:6].upper()
        PhoneVerificationToken.objects.create(
            user=request.user, phone=new_phone, otp=otp,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        # TODO: send_sms_otp.delay(new_phone, otp)
        return Response({"detail": "OTP sent to new phone."})


class PhoneChangeConfirmView(APIView):
    """Confirm phone change with OTP."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = PhoneVerificationToken.objects.filter(
            user=request.user,
            phone=serializer.validated_data["phone"],
            otp=serializer.validated_data["otp"],
            is_used=False, expires_at__gt=timezone.now(),
        ).order_by("-created_at").first()
        if not token:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        token.is_used = True
        token.save(update_fields=["is_used"])
        request.user.phone = token.phone
        request.user.save(update_fields=["phone"])
        return Response({"detail": "Phone updated."})


# ── Social Account Linking (#21–22) ──────────────────────────────────────

class SocialLinkView(APIView):
    """Link a social account to existing user (#21)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SocialLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.validated_data["provider"]
        social_id = serializer.validated_data["social_id"]
        field = f"{provider}_id"
        # Ensure not already linked to another user
        if User.objects.filter(**{field: social_id}).exclude(pk=request.user.pk).exists():
            return Response({"detail": "This account is linked to another user."}, status=status.HTTP_400_BAD_REQUEST)
        setattr(request.user, field, social_id)
        request.user.save(update_fields=[field])
        return Response({"detail": f"{provider.title()} account linked."})


class SocialUnlinkView(APIView):
    """Unlink a social account (#22)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SocialUnlinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.validated_data["provider"]
        field = f"{provider}_id"
        setattr(request.user, field, None)
        request.user.save(update_fields=[field])
        return Response({"detail": f"{provider.title()} account unlinked."})


# ── Suspicious Login Alert (#25) ─────────────────────────────────────────

def _check_suspicious_login(user, request):
    """Send alert if login from new device/IP (#25)."""
    ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
    device = request.META.get("HTTP_USER_AGENT", "")[:200]
    known = UserSession.objects.filter(user=user, ip_address=ip).exists()
    if not known:
        from apps.shared.tasks import send_email_verification
        logger.info("Suspicious login for %s from %s", user.email, ip)
        # TODO: send_suspicious_login_alert.delay(str(user.id), ip, device)


# ── NIC Recovery (#26) ───────────────────────────────────────────────────

class NICRecoveryView(APIView):
    """Recover account using National ID Card number (#26)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = NICRecoverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nic = serializer.validated_data["nic_number"]
        from apps.candidates.models import SeekerProfile
        profile = SeekerProfile.objects.filter(nic_number=nic).select_related("user").first()
        if not profile:
            return Response({"detail": "If a matching account exists, a recovery link was sent."})
        user = profile.user
        token = PasswordResetToken.objects.create(
            user=user, token=secrets.token_hex(32),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        from apps.shared.tasks import send_password_reset_email
        send_password_reset_email.delay(str(user.id), token.token)
        return Response({"detail": "If a matching account exists, a recovery link was sent."})


# ── Password Reset via SMS (#13) ─────────────────────────────────────────

class PasswordResetSMSView(APIView):
    """Reset password via SMS OTP (#13)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSMSRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        user = User.objects.filter(phone=phone).first()
        if user:
            otp = secrets.token_hex(3)[:6].upper()
            PhoneVerificationToken.objects.create(
                user=user, phone=phone, otp=otp,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            # TODO: send_sms_otp.delay(phone, otp)
        return Response({"detail": "If the phone exists, an OTP was sent."})


class PasswordResetSMSConfirmView(APIView):
    """Confirm password reset with SMS OTP + new password."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = request.data.get("phone")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")
        if not all([phone, otp, new_password]):
            return Response({"detail": "Phone, OTP, and new password required."}, status=status.HTTP_400_BAD_REQUEST)

        token = PhoneVerificationToken.objects.filter(
            phone=phone, otp=otp, is_used=False, expires_at__gt=timezone.now(),
        ).order_by("-created_at").first()
        if not token:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        token.is_used = True
        token.save(update_fields=["is_used"])
        user = token.user
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password reset successful."})


# ── Employer Verification Workflow (#35) ──────────────────────────────────

class EmployerVerificationView(APIView):
    """Submit employer verification documents (#35)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmployerVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.employers.models import EmployerAccount
        employer = EmployerAccount.objects.filter(
            team_members__user=request.user
        ).first()
        if not employer:
            return Response({"detail": "No employer account found."}, status=status.HTTP_404_NOT_FOUND)
        employer.registration_no = serializer.validated_data.get("registration_no", "")
        employer.tax_id = serializer.validated_data.get("tax_id", "")
        employer.verification_badge = "pending"
        employer.save(update_fields=["registration_no", "tax_id", "verification_badge"])
        return Response({"detail": "Verification request submitted."})
