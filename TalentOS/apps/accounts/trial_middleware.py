"""
Trial/Subscription middleware — enforces subscription status on every API request.
Exempt: /auth/, /health/, /api/docs/, /admin/
"""
from django.http import JsonResponse
from django.utils import timezone
import re

EXEMPT_PATHS = re.compile(
    r'^/(api/v1/auth/|api/v1/portal/|health/|ready/|api/docs/|api/schema/|admin/|__debug__/)'
)


class TrialMiddleware:
    """
    Checks subscription status and blocks access for expired/canceled tenants.
    Adds X-Trial-Days-Remaining header for active trials.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if EXEMPT_PATHS.match(request.path):
            return self.get_response(request)

        # Only apply to authenticated API requests with a tenant
        if hasattr(request, 'tenant') and request.user.is_authenticated:
            result = self._check_subscription(request.tenant)
            if result is not None:
                return result

        response = self.get_response(request)

        # Append trial info headers
        if hasattr(request, 'tenant'):
            try:
                sub = request.tenant.subscription
                if sub.status == 'trialing':
                    response['X-Trial-Days-Remaining'] = str(sub.trial_days_remaining)
                    response['X-Subscription-Status'] = 'trialing'
                else:
                    response['X-Subscription-Status'] = sub.status
            except Exception:
                pass

        return response

    def _check_subscription(self, tenant):
        try:
            sub = tenant.subscription
        except Exception:
            return None  # No subscription record — allow (legacy / unconfigured)

        if sub.status in ('active', 'trialing', 'grace_period'):
            return None

        if sub.status in ('expired', 'canceled'):
            return JsonResponse({
                'error': 'subscription_expired',
                'message': 'Your subscription has expired. Please renew to continue.',
                'status': sub.status,
                'upgrade_url': '/billing/upgrade/',
            }, status=402)

        if sub.status == 'past_due':
            return JsonResponse({
                'error': 'payment_past_due',
                'message': 'Payment is past due. Please update your payment method.',
                'status': 'past_due',
                'billing_url': '/billing/',
            }, status=402)

        return None
