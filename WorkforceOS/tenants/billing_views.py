"""Billing API views for HRM."""
import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema

from .billing import create_checkout_session, create_billing_portal_session, cancel_subscription
from .enterprise import Subscription

logger = logging.getLogger(__name__)


class CreateCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Billing'], summary='Create Stripe checkout session')
    def post(self, request):
        plan = request.data.get('plan', 'starter')
        billing_cycle = request.data.get('billing_cycle', 'monthly')

        price_map = {
            ('starter', 'monthly'): getattr(settings, 'STRIPE_PRICE_STARTER_MONTHLY', ''),
            ('starter', 'annual'): getattr(settings, 'STRIPE_PRICE_STARTER_ANNUAL', ''),
            ('professional', 'monthly'): getattr(settings, 'STRIPE_PRICE_PRO_MONTHLY', ''),
            ('professional', 'annual'): getattr(settings, 'STRIPE_PRICE_PRO_ANNUAL', ''),
            ('enterprise', 'monthly'): getattr(settings, 'STRIPE_PRICE_ENTERPRISE_MONTHLY', ''),
            ('enterprise', 'annual'): getattr(settings, 'STRIPE_PRICE_ENTERPRISE_ANNUAL', ''),
        }
        price_id = price_map.get((plan, billing_cycle), '')
        if not price_id:
            return Response({'error': 'Invalid plan or billing cycle.'}, status=status.HTTP_400_BAD_REQUEST)

        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://app.connectos.io')
        try:
            result = create_checkout_session(
                tenant=request.user.tenant,
                admin_email=request.user.email,
                price_id=price_id,
                success_url=f'{frontend_url}/settings/billing?success=1',
                cancel_url=f'{frontend_url}/settings/billing?cancelled=1',
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error('Checkout session creation failed: %s', e)
            return Response({'error': 'Failed to create checkout session.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BillingPortalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Billing'], summary='Open Stripe billing portal')
    def post(self, request):
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://app.connectos.io')
        try:
            result = create_billing_portal_session(
                tenant=request.user.tenant,
                return_url=f'{frontend_url}/settings/billing',
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error('Billing portal failed: %s', e)
            return Response({'error': 'Failed to open billing portal.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CancelSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Billing'], summary='Cancel subscription at period end')
    def post(self, request):
        cancelled = cancel_subscription(request.user.tenant)
        if not cancelled:
            return Response({'error': 'No active subscription to cancel.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Subscription will be cancelled at the end of the billing period.'})


class SubscriptionStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Billing'], summary='Get current subscription status')
    def get(self, request):
        sub = getattr(request.user.tenant, 'subscription', None)
        if not sub:
            return Response({'status': 'no_subscription', 'plan': None})
        return Response({
            'status': sub.status,
            'plan': sub.plan,
            'billing_cycle': sub.billing_cycle,
            'trial_ends_at': sub.trial_ends_at,
            'days_remaining': sub.days_remaining,
            'is_active': sub.is_active,
            'max_users': sub.max_users,
            'current_users': sub.current_users,
        })
