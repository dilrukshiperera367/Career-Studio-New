"""Tenant middleware — resolves tenant for every request, enforces trial limits."""

import logging
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from tenants.models import Tenant

logger = logging.getLogger('hrm')


class TenantMiddleware:
    """
    Resolves tenant from JWT claims or X-Tenant-ID header.
    Sets request.tenant and request.tenant_id for downstream use.
    Skips tenant resolution for public endpoints (auth, docs, admin).
    """

    EXEMPT_PATHS = [
        '/admin/',
        '/api/docs/',
        '/api/schema/',
        '/api/v1/auth/login',
        '/api/v1/auth/register',
        '/api/v1/auth/token',
        '/health/',
        '/ready/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip tenant resolution for exempt paths
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            request.tenant = None
            request.tenant_id = None
            return self.get_response(request)

        # Try to resolve tenant
        tenant_id = self._resolve_tenant_id(request)

        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
                if tenant.status in ('active', 'trial'):
                    request.tenant = tenant
                    request.tenant_id = tenant.id
                else:
                    return JsonResponse(
                        {'error': {'code': 'TENANT_INACTIVE', 'message': 'Tenant account is not active'}},
                        status=403
                    )
            except Tenant.DoesNotExist:
                return JsonResponse(
                    {'error': {'code': 'TENANT_NOT_FOUND', 'message': 'Tenant not found'}},
                    status=404
                )
        else:
            request.tenant = None
            request.tenant_id = None

        return self.get_response(request)

    def _resolve_tenant_id(self, request):
        """Resolve tenant ID from JWT claims, header, or user."""
        # 1. From JWT claims (set by authentication)
        if hasattr(request, 'user') and hasattr(request.user, 'tenant_id') and request.user.tenant_id:
            return request.user.tenant_id

        # 2. From explicit header (for API key auth)
        tenant_header = request.META.get('HTTP_X_TENANT_ID')
        if tenant_header:
            return tenant_header

        return None


class TrialEnforcementMiddleware:
    """
    Enforces trial expiration for HRM:
    - Active trial: full access
    - Grace period (3 days after expiry): read-only access
    - Expired past grace: blocked with upgrade prompt
    """

    GRACE_PERIOD_DAYS = 3

    # Paths that bypass trial enforcement
    EXEMPT_PATHS = [
        '/admin/',
        '/api/docs/',
        '/api/schema/',
        '/api/v1/auth/',
        '/api/v1/tenants/trial-status',
        '/api/v1/tenants/subscription',
        '/health/',
        '/ready/',
    ]

    # Read-only methods allowed during grace period
    READ_ONLY_METHODS = {'GET', 'HEAD', 'OPTIONS'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for exempt paths
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return self.get_response(request)

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return self.get_response(request)

        # Active paid subscription — no restrictions
        if tenant.status == 'active':
            return self.get_response(request)

        # Active trial — check if still within trial period
        if tenant.status == 'trial' and tenant.trial_ends_at:
            if timezone.now() <= tenant.trial_ends_at:
                # Trial still active
                return self.get_response(request)

            # Trial expired — check grace period
            grace_end = tenant.trial_ends_at + timedelta(days=self.GRACE_PERIOD_DAYS)

            if timezone.now() <= grace_end:
                # Grace period — read-only access
                if request.method not in self.READ_ONLY_METHODS:
                    return JsonResponse({
                        'error': {
                            'code': 'TRIAL_GRACE_PERIOD',
                            'message': 'Your trial has expired. You have read-only access for 3 more days. Please upgrade to continue.',
                            'trial_ends_at': tenant.trial_ends_at.isoformat(),
                            'grace_ends_at': grace_end.isoformat(),
                            'upgrade_url': '/pricing',
                        }
                    }, status=403)
                return self.get_response(request)

            # Past grace period — fully blocked
            return JsonResponse({
                'error': {
                    'code': 'TRIAL_EXPIRED',
                    'message': 'Your free trial has expired. Please upgrade to a paid plan to continue using ConnectOS HRM.',
                    'trial_ends_at': tenant.trial_ends_at.isoformat(),
                    'upgrade_url': '/pricing',
                }
            }, status=403)

        # Trial status but no trial_ends_at — allow access (legacy data)
        if tenant.status == 'trial':
            return self.get_response(request)

        # Suspended/cancelled
        if tenant.status in ('suspended', 'cancelled'):
            return JsonResponse({
                'error': {
                    'code': 'ACCOUNT_SUSPENDED',
                    'message': 'Your account is suspended. Please contact support.',
                }
            }, status=403)

        return self.get_response(request)
