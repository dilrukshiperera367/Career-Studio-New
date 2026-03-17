"""Views for accounts app — Auth and user management."""

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.accounts.models import User
from apps.accounts.serializers import (
    UserSerializer, UserCreateSerializer, TokenObtainSerializer,
    CompanyRegisterSerializer, CandidateRegisterSerializer,
)
from apps.accounts.permissions import IsTenantAdmin


def _send_welcome_email(user, tenant):
    """Send welcome email to new registrant."""
    try:
        app_url = getattr(settings, 'FRONTEND_URL', 'https://app.connectos.io')
        trial_ends = tenant.trial_ends_at.strftime('%B %d, %Y') if tenant.trial_ends_at else '14 days from now'
        context = {
            'user_name': user.get_full_name() or user.email,
            'company_name': tenant.name,
            'trial_ends_at': trial_ends,
            'app_url': app_url,
        }
        subject = f'Welcome to ConnectOS, {tenant.name}!'
        html_body = render_to_string('email/welcome.html', context)
        text_body = (
            f'Hi {context["user_name"]},\n\n'
            f'Welcome to ConnectOS! Your 14-day free trial has started.\n'
            f'Visit {app_url}/dashboard to get started.\n\n'
            f'Your trial expires on {trial_ends}.\n'
        )
        msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass  # Never block registration due to email failure


def _send_verification_email(user):
    """Send email verification link to a newly registered user. (#17)"""
    import secrets
    from datetime import timedelta
    from django.utils import timezone
    from apps.accounts.models import EmailVerificationToken

    try:
        # Clean up any prior unused tokens
        EmailVerificationToken.objects.filter(user=user, used=False).delete()

        token_str = secrets.token_urlsafe(48)
        expires = timezone.now() + timedelta(hours=24)
        EmailVerificationToken.objects.create(user=user, token=token_str, expires_at=expires)

        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://app.connectos.co')
        verify_url = f"{frontend_url}/verify-email?token={token_str}"

        from django.core.mail import send_mail
        send_mail(
            subject='Verify your email address — ConnectATS',
            message=(
                f'Hi {user.first_name},\n\n'
                f'Please verify your email address:\n\n{verify_url}\n\n'
                f'This link expires in 24 hours.'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@connectos.co'),
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass  # Never block registration due to email failure


@extend_schema(
    summary='Register a new company',
    description='Creates a tenant, admin user, and starts 14-day trial.',
    responses={201: OpenApiResponse(description='Registration successful with JWT tokens')},
    tags=['Authentication'],
)
class CompanyRegisterView(generics.CreateAPIView):
    """Register a new company + admin user. Starts 14-day trial. Returns JWT tokens."""
    serializer_class = CompanyRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        _send_welcome_email(user, user.tenant)
        _send_verification_email(user)  # #17 — trigger email verification
        refresh = RefreshToken.for_user(user)
        # Add custom claims
        refresh["tenant_id"] = str(user.tenant_id)
        refresh["user_type"] = user.user_type
        refresh["email"] = user.email
        refresh["first_name"] = user.first_name
        refresh["active_product"] = "ats"
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "trial": {
                "is_trial": True,
                "days_remaining": 14,
                "trial_ends_at": user.tenant.trial_ends_at.isoformat() if user.tenant.trial_ends_at else None,
            },
        }, status=status.HTTP_201_CREATED)


class CandidateRegisterView(generics.CreateAPIView):
    """Register a new candidate user. Returns JWT tokens."""
    serializer_class = CandidateRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _send_verification_email(user)  # #17 — trigger email verification
        refresh = RefreshToken.for_user(user)
        refresh["user_type"] = user.user_type
        refresh["email"] = user.email
        refresh["first_name"] = user.first_name
        refresh["active_product"] = "ats"
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class RegisterView(generics.CreateAPIView):
    """Legacy register endpoint."""
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    """JWT login with tenant_id + user_type in token."""
    serializer_class = TokenObtainSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """Get/update current user profile."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """List users in the tenant (admin only)."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get_queryset(self):
        return User.objects.filter(tenant_id=self.request.tenant_id)


# ---------------------------------------------------------------------------
# Password reset flow
# ---------------------------------------------------------------------------


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ — change password while authenticated.

    Security (#73): after a successful password change, all outstanding
    refresh tokens for this user are blacklisted so previously issued tokens
    cannot be reused.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        if not old_password or not new_password:
            return Response({"error": "old_password and new_password required"}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(old_password):
            return Response({"error": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_password)
        request.user.save()

        # Invalidate all outstanding JWT refresh tokens for this user (#73)
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            from rest_framework_simplejwt.tokens import RefreshToken as _RT
            for token in OutstandingToken.objects.filter(user=request.user):
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            pass  # simplejwt blacklist app may not be installed

        return Response({"message": "Password updated successfully. Please log in again."})


class ForgotPasswordView(APIView):
    """POST /api/v1/auth/forgot-password/ — send reset email.

    Rate-limited to 5 requests/hour per IP to prevent email bombing (#71).
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        import secrets
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        from apps.accounts.models import PasswordResetToken

        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"error": "email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "If that email exists, a reset link has been sent."})

        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        token_str = secrets.token_urlsafe(64)
        from django.utils import timezone
        expires = timezone.now() + timedelta(hours=2)
        PasswordResetToken.objects.create(user=user, token=token_str, expires_at=expires)

        frontend_url = getattr(django_settings, "FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/reset-password?token={token_str}"

        try:
            send_mail(
                subject="Reset your password",
                message=f"Click the link below to reset your password (valid for 2 hours):\n\n{reset_link}",
                from_email=getattr(django_settings, "DEFAULT_FROM_EMAIL", "noreply@ats.local"),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({"message": "If that email exists, a reset link has been sent."})


class ResetPasswordView(APIView):
    """POST /api/v1/auth/reset-password/ — validate token and set new password."""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.utils import timezone
        from apps.accounts.models import PasswordResetToken

        token_str = request.data.get("token", "").strip()
        new_password = request.data.get("new_password", "")

        if not token_str or not new_password:
            return Response({"error": "token and new_password are required"}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_token = PasswordResetToken.objects.select_related("user").get(
                token=token_str, used=False
            )
        except PasswordResetToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > reset_token.expires_at:
            return Response({"error": "Token has expired"}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(new_password)
        user.save()
        reset_token.used = True
        reset_token.save(update_fields=["used"])

        return Response({"message": "Password reset successfully"})


# ---------------------------------------------------------------------------
# Invite flow
# ---------------------------------------------------------------------------


class InviteUserView(APIView):
    """POST /api/v1/auth/invite/ — invite a team member to the tenant."""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request):
        import secrets
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        from django.utils import timezone
        from apps.accounts.models import InviteToken

        email = request.data.get("email", "").strip().lower()
        user_type = request.data.get("user_type", "recruiter")

        if not email:
            return Response({"error": "email is required"}, status=status.HTTP_400_BAD_REQUEST)

        valid_types = ["recruiter", "hiring_manager", "interviewer"]
        if user_type not in valid_types:
            return Response({"error": f"user_type must be one of: {valid_types}"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email, tenant=request.tenant).exists():
            return Response({"error": "User already exists in this tenant"}, status=status.HTTP_409_CONFLICT)

        token_str = secrets.token_urlsafe(64)
        expires = timezone.now() + timedelta(days=7)

        invite, _ = InviteToken.objects.update_or_create(
            tenant=request.tenant,
            email=email,
            defaults={
                "invited_by": request.user,
                "user_type": user_type,
                "token": token_str,
                "expires_at": expires,
                "accepted": False,
            },
        )

        frontend_url = getattr(django_settings, "FRONTEND_URL", "http://localhost:3000")
        invite_link = f"{frontend_url}/accept-invite?token={invite.token}"

        try:
            send_mail(
                subject=f"You've been invited to {request.tenant.name}",
                message=(
                    f"You've been invited to join {request.tenant.name} on ATS.\n\n"
                    f"Accept the invitation here (valid 7 days):\n\n{invite_link}"
                ),
                from_email=getattr(django_settings, "DEFAULT_FROM_EMAIL", "noreply@ats.local"),
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({"message": "Invite sent", "invite_id": str(invite.id)}, status=status.HTTP_201_CREATED)


class InviteAcceptView(APIView):
    """POST /api/v1/auth/invite-accept/ — accept invite and create account."""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.utils import timezone
        from apps.accounts.models import InviteToken

        token_str = request.data.get("token", "").strip()
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        password = request.data.get("password", "")

        if not all([token_str, first_name, last_name, password]):
            return Response(
                {"error": "token, first_name, last_name, and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invite = InviteToken.objects.select_related("tenant").get(
                token=token_str, accepted=False
            )
        except InviteToken.DoesNotExist:
            return Response({"error": "Invalid or already used invite token"}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > invite.expires_at:
            return Response({"error": "Invite has expired"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=invite.email).exists():
            return Response({"error": "An account with this email already exists"}, status=status.HTTP_409_CONFLICT)

        user = User.objects.create_user(
            email=invite.email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            tenant=invite.tenant,
            user_type=invite.user_type,
        )

        invite.accepted = True
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["accepted", "accepted_at"])

        refresh = RefreshToken.for_user(user)
        refresh["tenant_id"] = str(user.tenant_id)
        refresh["user_type"] = user.user_type
        refresh["email"] = user.email
        refresh["first_name"] = user.first_name
        refresh["active_product"] = "ats"

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class UserDeactivateView(APIView):
    """POST /api/v1/auth/users/<id>/deactivate/ — deactivate a user."""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, tenant=request.tenant)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user:
            return Response({"error": "Cannot deactivate yourself"}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response({"message": "User deactivated"})


# ---------------------------------------------------------------------------
# Invitation Management (#52) — list, cancel, resend pending invites
# ---------------------------------------------------------------------------

class InviteManagementView(APIView):
    """
    GET  /api/v1/auth/invites/          — list pending invitations for this tenant
    DELETE /api/v1/auth/invites/<id>/   — cancel / revoke a pending invite
    POST /api/v1/auth/invites/<id>/resend/ — resend the invitation email
    """
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request):
        from apps.accounts.models import InviteToken
        from django.utils import timezone
        qs = InviteToken.objects.filter(
            tenant=request.tenant,
            accepted=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').values(
            'id', 'email', 'user_type', 'created_at', 'expires_at'
        )
        return Response({'data': list(qs)})


class InviteCancelView(APIView):
    """DELETE /api/v1/auth/invites/<id>/ — revoke a pending invite."""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def delete(self, request, invite_id):
        from apps.accounts.models import InviteToken
        try:
            invite = InviteToken.objects.get(id=invite_id, tenant=request.tenant, accepted=False)
        except InviteToken.DoesNotExist:
            return Response({'error': 'Invite not found or already accepted'}, status=status.HTTP_404_NOT_FOUND)
        invite.delete()
        return Response({'message': 'Invite revoked'}, status=status.HTTP_204_NO_CONTENT)


class InviteResendView(APIView):
    """POST /api/v1/auth/invites/<id>/resend/ — re-send the invitation email and refresh expiry."""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request, invite_id):
        from apps.accounts.models import InviteToken
        from django.utils import timezone
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings

        try:
            invite = InviteToken.objects.get(id=invite_id, tenant=request.tenant, accepted=False)
        except InviteToken.DoesNotExist:
            return Response({'error': 'Invite not found or already accepted'}, status=status.HTTP_404_NOT_FOUND)

        # Refresh expiry
        invite.expires_at = timezone.now() + timedelta(days=7)
        invite.save(update_fields=['expires_at'])

        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://app.connectos.co')
        invite_link = f"{frontend_url}/accept-invite?token={invite.token}"
        try:
            send_mail(
                subject=f"Reminder: You're invited to {request.tenant.name}",
                message=(
                    f"You have a pending invitation to join {request.tenant.name} on ATS.\n\n"
                    f"Accept the invitation here (valid 7 days):\n\n{invite_link}"
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@connectos.co'),
                recipient_list=[invite.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({'message': 'Invite resent', 'expires_at': invite.expires_at.isoformat()})




class MFAEnableView(APIView):
    """POST /api/v1/auth/mfa/enable/
    Step 1: Generate a TOTP secret and return a QR code URI.
    The user scans the QR code in their authenticator app, then calls /mfa/verify/.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import base64
        try:
            import pyotp
        except ImportError:
            return Response(
                {"error": "pyotp is not installed. Run: pip install pyotp"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        user = request.user
        if user.mfa_enabled:
            return Response({"error": "MFA is already enabled"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate new secret (32-char Base32)
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.save(update_fields=["mfa_secret"])

        totp = pyotp.TOTP(secret)
        app_name = "ConnectATS"
        provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=app_name)

        # Try to generate QR code as base64 PNG
        qr_code_b64 = None
        try:
            import qrcode
            import io as _io
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            qr_code_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            pass  # qrcode not installed; client can render from provisioning_uri

        return Response({
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": qr_code_b64,
            "message": "Scan the QR code with your authenticator app, then call /mfa/verify/ to confirm.",
        })


class MFAVerifyView(APIView):
    """POST /api/v1/auth/mfa/verify/
    Step 2: Confirm MFA setup by submitting a valid TOTP code.
    Also used for MFA challenge during login.

    Body: { "code": "123456" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            import pyotp
        except ImportError:
            return Response(
                {"error": "pyotp is not installed. Run: pip install pyotp"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        code = request.data.get("code", "").strip()
        if not code:
            return Response({"error": "code is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.mfa_secret:
            return Response(
                {"error": "MFA not configured. Call /mfa/enable/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code, valid_window=1):
            return Response({"error": "Invalid TOTP code"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.mfa_enabled:
            user.mfa_enabled = True
            user.save(update_fields=["mfa_enabled"])
            return Response({"message": "MFA enabled successfully", "mfa_enabled": True})

        return Response({"message": "Code verified", "mfa_enabled": True})


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — blacklist the refresh token to invalidate the session."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"error": "Invalid or already blacklisted token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MFADisableView(APIView):
    """POST /api/v1/auth/mfa/disable/
    Disable MFA. Requires a valid TOTP code as confirmation.
    Body: { "code": "123456" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            import pyotp
        except ImportError:
            return Response(
                {"error": "pyotp is not installed."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        user = request.user
        if not user.mfa_enabled:
            return Response({"error": "MFA is not enabled"}, status=status.HTTP_400_BAD_REQUEST)

        code = request.data.get("code", "").strip()
        if not code:
            return Response({"error": "code is required to disable MFA"}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code, valid_window=1):
            return Response({"error": "Invalid TOTP code"}, status=status.HTTP_400_BAD_REQUEST)

        user.mfa_enabled = False
        user.mfa_secret = ""
        user.save(update_fields=["mfa_enabled", "mfa_secret"])
        return Response({"message": "MFA disabled successfully", "mfa_enabled": False})


class UserPermissionsView(APIView):
    """GET /api/v1/auth/me/permissions/ — current user's roles and capabilities."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Accounts'], summary='Get current user permissions')
    def get(self, request):
        from apps.accounts.permissions import _user_roles, ADMIN_ROLES, RECRUITER_ROLES
        roles = list(_user_roles(request.user))
        return Response({
            'user_id': str(request.user.id),
            'email': request.user.email,
            'roles': roles,
            'capabilities': {
                'can_manage_jobs': bool(set(roles) & RECRUITER_ROLES),
                'can_manage_candidates': bool(set(roles) & RECRUITER_ROLES),
                'can_admin': bool(set(roles) & ADMIN_ROLES),
                'can_interview': bool(roles),
            },
        })


# ---------------------------------------------------------------------------
# Email Verification  (#17)
# ---------------------------------------------------------------------------

class EmailVerificationSendView(APIView):
    """POST /api/v1/auth/email/verify/send/ — (re)send verification email."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import secrets
        from datetime import timedelta
        from django.utils import timezone
        from apps.accounts.models import EmailVerificationToken

        user = request.user
        if user.email_verified:
            return Response({'message': 'Email already verified'}, status=status.HTTP_200_OK)

        # Invalidate any existing unused tokens for this user
        EmailVerificationToken.objects.filter(user=user, used=False).delete()

        token_str = secrets.token_urlsafe(48)
        expires = timezone.now() + timedelta(hours=24)
        EmailVerificationToken.objects.create(
            user=user,
            token=token_str,
            expires_at=expires,
        )

        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://app.connectos.co')
        verify_url = f"{frontend_url}/verify-email?token={token_str}"

        try:
            from django.core.mail import send_mail
            send_mail(
                subject='Verify your email address — ConnectATS',
                message=(
                    f'Hi {user.first_name},\n\n'
                    f'Please verify your email address by clicking the link below:\n\n'
                    f'{verify_url}\n\n'
                    f'This link expires in 24 hours.\n\n'
                    f'If you did not create an account, you can ignore this email.'
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@connectos.co'),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({'message': 'Verification email sent'}, status=status.HTTP_200_OK)


class EmailVerificationConfirmView(APIView):
    """POST /api/v1/auth/email/verify/confirm/ — confirm token and mark email verified."""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.utils import timezone
        from apps.accounts.models import EmailVerificationToken

        token_str = request.data.get('token', '').strip()
        if not token_str:
            return Response({'error': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            evtoken = EmailVerificationToken.objects.select_related('user').get(
                token=token_str, used=False
            )
        except EmailVerificationToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

        if evtoken.expires_at < timezone.now():
            return Response({'error': 'Token has expired. Request a new verification email.'}, status=status.HTTP_400_BAD_REQUEST)

        user = evtoken.user
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=['email_verified', 'email_verified_at'])

        evtoken.used = True
        evtoken.save(update_fields=['used'])

        return Response({'message': 'Email verified successfully', 'email': user.email})
