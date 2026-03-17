"""CampusOS — Accounts views."""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import EmailVerificationToken, PasswordResetToken, User
from .serializers import (
    CampusJWTSerializer,
    ChangePasswordSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Register a new CampusOS user account."""

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        self._send_verification_email(user)

    def _send_verification_email(self, user):
        token = secrets.token_hex(32)
        EmailVerificationToken.objects.create(
            user=user,
            token=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=24),
        )
        # Email delivery handled by Celery task (deferred)


class CampusTokenObtainView(TokenObtainPairView):
    """JWT login view returning enriched CampusOS token payload."""

    serializer_class = CampusJWTSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """Current user profile — GET and PATCH."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Authenticated password change."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """Verify email address via token."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_raw = request.data.get("token", "")
        if not token_raw:
            return Response({"detail": "Token required."}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
        try:
            record = EmailVerificationToken.objects.select_related("user").get(
                token=token_hash
            )
        except EmailVerificationToken.DoesNotExist:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        if not record.is_valid():
            return Response(
                {"detail": "Token expired or already used."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record.used_at = timezone.now()
        record.save(update_fields=["used_at"])
        record.user.email_verified = True
        record.user.save(update_fields=["email_verified", "updated_at"])
        return Response({"detail": "Email verified."})


class RequestPasswordResetView(APIView):
    """Request a password reset email."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        # Always return 200 to prevent email enumeration
        try:
            user = User.objects.get(email=email, is_active=True)
            token = secrets.token_hex(32)
            PasswordResetToken.objects.create(
                user=user,
                token=hashlib.sha256(token.encode()).hexdigest(),
                expires_at=timezone.now() + timedelta(hours=2),
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            # Celery task sends the email
        except User.DoesNotExist:
            pass
        return Response({"detail": "If this email exists, a reset link has been sent."})


class ConfirmPasswordResetView(APIView):
    """Confirm password reset with token + new password."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_raw = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
        try:
            record = PasswordResetToken.objects.select_related("user").get(token=token_hash)
        except PasswordResetToken.DoesNotExist:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

        if not record.is_valid():
            return Response(
                {"detail": "Token expired or already used."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record.user.set_password(new_password)
        record.user.save(update_fields=["password", "updated_at"])
        record.used_at = timezone.now()
        record.save(update_fields=["used_at"])
        return Response({"detail": "Password reset successful."})
