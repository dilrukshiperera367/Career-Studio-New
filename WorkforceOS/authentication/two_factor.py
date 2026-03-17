"""
Two-Factor Authentication (2FA) stubs.
Full implementation requires: pip install pyotp qrcode[pil]
"""
from __future__ import annotations
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers, status

logger = logging.getLogger('hrm.auth')


class TwoFactorEnrollSerializer(serializers.Serializer):
    """Begin TOTP enrollment."""
    password = serializers.CharField(write_only=True)


class TwoFactorVerifySerializer(serializers.Serializer):
    """Verify a TOTP code."""
    code = serializers.CharField(max_length=8, min_length=6)


class TwoFactorEnrollView(APIView):
    """
    POST /api/v1/auth/2fa/enroll/
    Returns a TOTP secret and QR code URI for authenticator app setup.
    Requires pyotp: pip install pyotp qrcode
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TwoFactorEnrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            import pyotp
        except ImportError:
            return Response(
                {'detail': '2FA is not yet enabled on this server. Contact your administrator.'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )

        # Generate a new TOTP secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        issuer = 'ConnectOS HRM'
        uri = totp.provisioning_uri(name=request.user.email, issuer_name=issuer)

        # Store secret temporarily in session (finalize on verify)
        request.session['totp_pending_secret'] = secret

        return Response({
            'secret': secret,
            'otpauth_uri': uri,
            'message': 'Scan the QR code with your authenticator app, then call /verify/ with a code.',
        })


class TwoFactorVerifyView(APIView):
    """
    POST /api/v1/auth/2fa/verify/
    Confirm TOTP code to complete enrollment or re-authenticate.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            import pyotp
        except ImportError:
            return Response({'detail': '2FA not enabled.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

        code = serializer.validated_data['code']

        # Check for pending enrollment
        pending_secret = request.session.get('totp_pending_secret')
        if pending_secret:
            totp = pyotp.TOTP(pending_secret)
            if totp.verify(code, valid_window=1):
                # TODO: persist secret to user profile / 2fa model
                del request.session['totp_pending_secret']
                logger.info('2FA enrolled for user %s', request.user.id)
                return Response({'detail': '2FA enrollment successful.', 'enabled': True})
            return Response({'detail': 'Invalid code. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

        # Existing 2FA verification
        # TODO: load stored TOTP secret from user profile
        return Response({'detail': 'No pending 2FA enrollment found.'}, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorDisableView(APIView):
    """
    POST /api/v1/auth/2fa/disable/
    Disable 2FA for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # TODO: clear TOTP secret from user profile after password confirmation
        return Response({'detail': '2FA has been disabled.', 'enabled': False})


class TwoFactorStatusView(APIView):
    """
    GET /api/v1/auth/2fa/status/
    Return current 2FA status for the user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # TODO: check user profile for totp_secret
        return Response({
            'enabled': False,
            'method': None,
            'message': 'Two-factor authentication is available. POST to /enroll/ to set it up.',
        })
