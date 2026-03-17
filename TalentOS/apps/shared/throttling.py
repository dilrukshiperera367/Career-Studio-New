"""Custom throttle classes for per-user and per-tenant rate limiting."""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class AuthenticatedUserThrottle(UserRateThrottle):
    """1000 requests/hour per authenticated user."""
    scope = 'user'
    rate = '1000/hour'


class AnonymousUserThrottle(AnonRateThrottle):
    """60 requests/hour per IP for anonymous requests."""
    scope = 'anon'
    rate = '60/hour'


class BurstUserThrottle(UserRateThrottle):
    """60 requests/minute burst limit per authenticated user."""
    scope = 'burst'
    rate = '60/min'


class TenantThrottle(SimpleRateThrottle):
    """
    Rate limit per tenant (for multi-tenant SaaS fairness).
    500 requests/minute across all users of a tenant.
    """
    scope = 'tenant'
    rate = '500/min'

    def get_cache_key(self, request, view):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None  # no limit if no tenant context
        return self.cache_format % {
            'scope': self.scope,
            'ident': str(getattr(tenant, 'id', str(tenant))),
        }
