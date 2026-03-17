"""Tenant middleware — sets tenant context for RLS and query scoping, enforces trial limits."""

import logging
from datetime import timedelta
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

# Paths that don't require tenant context
TENANT_EXEMPT_PATHS = [
    "/admin/",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/portal/apply",
    "/health/",
    "/ready/",
]

# Paths that bypass trial enforcement (read-only allowed after expiry)
TRIAL_EXEMPT_PATHS = [
    "/admin/",
    "/api/v1/auth/",
    "/api/v1/tenants/trial-status",
    "/api/v1/tenants/subscription",
    "/api/v1/tenants/current",
    "/health/",
    "/ready/",
]

# Read-only methods allowed during grace period
GRACE_PERIOD_METHODS = {"GET", "HEAD", "OPTIONS"}


class TenantMiddleware:
    """
    Extract tenant_id from JWT token and set it on the database connection
    for PostgreSQL RLS enforcement.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip tenant context for exempt paths
        if any(request.path.startswith(p) for p in TENANT_EXEMPT_PATHS):
            request.tenant_id = None
            return self.get_response(request)

        tenant_id = self._extract_tenant_id(request)
        request.tenant_id = tenant_id

        if tenant_id:
            # Only set RLS context on PostgreSQL
            db_engine = connection.settings_dict.get("ENGINE", "")
            if "postgresql" in db_engine:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SET LOCAL app.tenant_id = %s", [str(tenant_id)]
                        )
                except Exception:
                    pass  # SQLite or other non-PG engine

        response = self.get_response(request)
        return response

    def _extract_tenant_id(self, request):
        """Extract tenant_id from JWT token or header."""
        # Try JWT first
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(
                jwt_auth.get_raw_token(jwt_auth.get_header(request))
            )
            return validated_token.get("tenant_id")
        except Exception:
            pass

        # Fallback: explicit header
        return request.headers.get("X-Tenant-ID")


class TrialEnforcementMiddleware:
    """
    Enforces trial expiration:
    - Active trial: full access
    - Grace period (3 days after expiry): read-only access
    - Expired past grace: blocked with upgrade prompt
    """

    GRACE_PERIOD_DAYS = 3

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for exempt paths
        if any(request.path.startswith(p) for p in TRIAL_EXEMPT_PATHS):
            return self.get_response(request)

        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            return self.get_response(request)

        # Check trial status
        from apps.tenants.models import Tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return self.get_response(request)

        # Active paid subscription — no restrictions
        if tenant.status == "active":
            return self.get_response(request)

        # Active trial — no restrictions
        if tenant.status == "trial" and not tenant.is_trial_expired:
            return self.get_response(request)

        # Trial expired — check grace period
        if tenant.trial_ends_at:
            grace_end = tenant.trial_ends_at + timedelta(days=self.GRACE_PERIOD_DAYS)

            if timezone.now() <= grace_end:
                # Grace period — read-only access
                if request.method not in GRACE_PERIOD_METHODS:
                    return JsonResponse({
                        "error": {
                            "code": "TRIAL_GRACE_PERIOD",
                            "message": "Your trial has expired. You have read-only access for 3 more days. Please upgrade to continue.",
                            "trial_ends_at": tenant.trial_ends_at.isoformat(),
                            "grace_ends_at": grace_end.isoformat(),
                            "upgrade_url": "/pricing",
                        }
                    }, status=403)
                return self.get_response(request)

            # Past grace period — fully blocked
            return JsonResponse({
                "error": {
                    "code": "TRIAL_EXPIRED",
                    "message": "Your free trial has expired. Please upgrade to a paid plan to continue using ConnectOS.",
                    "trial_ends_at": tenant.trial_ends_at.isoformat(),
                    "upgrade_url": "/pricing",
                }
            }, status=403)

        # Expired or suspended status without trial_ends_at
        if tenant.status in ("expired", "suspended"):
            return JsonResponse({
                "error": {
                    "code": "ACCOUNT_SUSPENDED",
                    "message": "Your account is suspended. Please contact support.",
                }
            }, status=403)

        return self.get_response(request)
