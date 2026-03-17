"""Authentication views — register, login, profile, token refresh, password reset, invite."""

from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
)


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


class LoginView(TokenObtainPairView):
    """Login with email + password → returns JWT access + refresh tokens."""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    summary='Register a new company',
    description='Creates a tenant, admin user, and starts 14-day trial.',
    responses={201: OpenApiResponse(description='Registration successful with JWT tokens')},
    tags=['Authentication'],
)
class RegisterView(APIView):
    """Register new tenant + admin user. Starts 14-day free trial."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if user.tenant:
            _send_welcome_email(user, user.tenant)

        # Generate tokens
        token_serializer = CustomTokenObtainPairSerializer()
        token = token_serializer.get_token(user)

        return Response({
            'data': {
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(token.access_token),
                    'refresh': str(token),
                },
                'trial': {
                    'is_trial': True,
                    'days_remaining': 14,
                    'trial_ends_at': user.tenant.trial_ends_at.isoformat() if user.tenant and user.tenant.trial_ends_at else None,
                },
            },
            'meta': {'message': 'Registration successful. Your 14-day free trial has started!'}
        }, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get / update current user profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — blacklist the JWT refresh token (HTTP 205)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError

        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ — change password while authenticated.

    Security: invalidates all outstanding JWT refresh tokens after the change (#73).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not old_password or not new_password:
            return Response({'error': 'old_password and new_password required'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(old_password):
            return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 10:
            return Response({'error': 'Password must be at least 10 characters'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_password)
        request.user.save()

        # Blacklist all outstanding refresh tokens (#73)
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for token in OutstandingToken.objects.filter(user=request.user):
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            pass

        return Response({'message': 'Password updated successfully. Please log in again.'})


class ForgotPasswordView(APIView):
    """POST /api/v1/auth/forgot-password/ — send reset email.

    Rate-limited to prevent email bombing (#71).
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        import secrets
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from .models import PasswordResetToken

        User = get_user_model()
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'error': 'email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'If that email exists, a reset link has been sent.'})

        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        token_str = secrets.token_urlsafe(64)
        expires = timezone.now() + timedelta(hours=2)
        PasswordResetToken.objects.create(user=user, token=token_str, expires_at=expires)

        frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:5173')
        reset_link = f"{frontend_url}/reset-password?token={token_str}"

        try:
            send_mail(
                subject='Reset your password — HRM',
                message=f"Click the link below to reset your password (valid for 2 hours):\n\n{reset_link}",
                from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@hrm.local'),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({'message': 'If that email exists, a reset link has been sent.'})


class ResetPasswordView(APIView):
    """POST /api/v1/auth/reset-password/ — validate token and set new password."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.utils import timezone
        from .models import PasswordResetToken

        token_str = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')

        if not token_str or not new_password:
            return Response({'error': 'token and new_password are required'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 10:
            return Response({'error': 'Password must be at least 10 characters'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(
                token=token_str, used=False
            )
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > reset_token.expires_at:
            return Response({'error': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(new_password)
        user.save()
        reset_token.used = True
        reset_token.save(update_fields=['used'])

        return Response({'message': 'Password reset successfully'})


# ---------------------------------------------------------------------------
# Invite flow
# ---------------------------------------------------------------------------

class InviteUserView(APIView):
    """POST /api/v1/auth/invite/ — invite a user to the tenant."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import secrets
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from .models import InviteToken

        User = get_user_model()
        email = request.data.get('email', '').strip().lower()
        role_name = request.data.get('role_name', 'Employee')

        if not email:
            return Response({'error': 'email is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({'error': 'Tenant context required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email, tenant=request.tenant).exists():
            return Response({'error': 'User already exists in this tenant'}, status=status.HTTP_409_CONFLICT)

        token_str = secrets.token_urlsafe(64)
        expires = timezone.now() + timedelta(days=7)

        invite, _ = InviteToken.objects.update_or_create(
            tenant=request.tenant,
            email=email,
            defaults={
                'invited_by': request.user,
                'role_name': role_name,
                'token': token_str,
                'expires_at': expires,
                'accepted': False,
            },
        )

        frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:5173')
        invite_link = f"{frontend_url}/accept-invite?token={invite.token}"

        try:
            send_mail(
                subject=f"You've been invited to {request.tenant.name} HRM",
                message=(
                    f"You've been invited to join {request.tenant.name} on HRM.\n\n"
                    f"Accept the invitation here (valid 7 days):\n\n{invite_link}"
                ),
                from_email=getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@hrm.local'),
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({'message': 'Invite sent', 'invite_id': str(invite.id)}, status=status.HTTP_201_CREATED)


class InviteAcceptView(APIView):
    """POST /api/v1/auth/invite-accept/ — accept invite, create HRM account."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import RefreshToken
        from .models import InviteToken, Role, UserRole

        User = get_user_model()
        token_str = request.data.get('token', '').strip()
        first_name = request.data.get('first_name', '').strip()
        last_name = request.data.get('last_name', '').strip()
        password = request.data.get('password', '')

        if not all([token_str, first_name, last_name, password]):
            return Response(
                {'error': 'token, first_name, last_name, and password are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(password) < 10:
            return Response({'error': 'Password must be at least 10 characters'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invite = InviteToken.objects.select_related('tenant').get(
                token=token_str, accepted=False
            )
        except InviteToken.DoesNotExist:
            return Response({'error': 'Invalid or already used invite token'}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > invite.expires_at:
            return Response({'error': 'Invite has expired'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=invite.email).exists():
            return Response({'error': 'An account with this email already exists'}, status=status.HTTP_409_CONFLICT)

        user = User.objects.create_user(
            email=invite.email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            tenant_id=invite.tenant_id,
            status='active',
        )

        # Assign the invited role
        role, _ = Role.objects.get_or_create(
            name=invite.role_name,
            tenant=invite.tenant,
            defaults={'description': invite.role_name},
        )
        UserRole.objects.create(user=user, role=role)

        invite.accepted = True
        invite.accepted_at = timezone.now()
        invite.save(update_fields=['accepted', 'accepted_at'])

        refresh = RefreshToken.for_user(user)
        refresh['active_product'] = 'hrm'
        return Response({
            'data': {
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
            },
            'meta': {'message': 'Account created successfully'},
        }, status=status.HTTP_201_CREATED)
