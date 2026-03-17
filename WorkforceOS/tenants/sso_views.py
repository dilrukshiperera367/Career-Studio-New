"""SSO and SCIM configuration endpoints for enterprise tenants."""
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class SSOConfigSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['saml', 'oidc', 'oauth2'], required=True)
    entity_id = serializers.CharField(max_length=500, required=False, allow_blank=True)
    sso_url = serializers.URLField(required=False, allow_blank=True)
    certificate = serializers.CharField(required=False, allow_blank=True, style={'base_template': 'textarea.html'})
    client_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    client_secret = serializers.CharField(max_length=500, required=False, allow_blank=True, write_only=True)
    discovery_url = serializers.URLField(required=False, allow_blank=True)
    is_enabled = serializers.BooleanField(default=False)


class SCIMConfigSerializer(serializers.Serializer):
    is_enabled = serializers.BooleanField(default=False)
    scim_endpoint = serializers.CharField(read_only=True)
    bearer_token = serializers.CharField(read_only=True)


class SSOConfigView(APIView):
    """
    GET /api/v1/tenants/sso/
    PUT /api/v1/tenants/sso/
    """
    permission_classes = [IsAuthenticated]

    def _get_setting(self, request, key, default=None):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return default
        settings = getattr(tenant, 'settings', None) or {}
        if callable(getattr(settings, 'get', None)):
            return settings.get(key, default)
        return default

    def _save_setting(self, request, key, value):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False
        if not hasattr(tenant, 'settings'):
            return False
        settings = tenant.settings or {}
        settings[key] = value
        tenant.settings = settings
        tenant.save(update_fields=['settings'])
        return True

    def get(self, request):
        config = self._get_setting(request, 'sso_config', {})
        serializer = SSOConfigSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        serializer = SSOConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        saved = self._save_setting(request, 'sso_config', serializer.validated_data)
        if not saved:
            return Response({'detail': 'No tenant context — cannot save SSO config'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.validated_data)


class SCIMConfigView(APIView):
    """
    GET /api/v1/tenants/scim/
    POST /api/v1/tenants/scim/rotate-token/ — rotate the SCIM bearer token
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import uuid
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=400)
        tenant_id = getattr(tenant, 'id', 'unknown')
        tenant_slug = getattr(tenant, 'slug', str(tenant_id))
        settings = getattr(tenant, 'settings', {}) or {}
        return Response({
            'is_enabled': settings.get('scim_enabled', False),
            'scim_endpoint': f'/api/v1/scim/v2/{tenant_slug}/',
            'bearer_token': settings.get('scim_token_preview', '(not set — rotate to generate)'),
        })

    def post(self, request):
        """Rotate SCIM bearer token."""
        import secrets
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'No tenant context'}, status=400)
        new_token = secrets.token_urlsafe(40)
        settings = getattr(tenant, 'settings', {}) or {}
        settings['scim_token'] = new_token
        settings['scim_token_preview'] = new_token[:8] + '...'
        settings['scim_enabled'] = True
        tenant.settings = settings
        tenant.save(update_fields=['settings'])
        return Response({
            'bearer_token': new_token,
            'note': 'Store this token securely. It will not be shown again.',
        })
