"""Subscription management API endpoints."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta


class SubscriptionStatusView(APIView):
    """GET /api/v1/subscription/status/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = request.tenant.subscription
            return Response({
                'status': sub.status,
                'plan': sub.plan.tier if sub.plan else 'free_trial',
                'plan_name': sub.plan.name if sub.plan else 'Free Trial',
                'trial_end': sub.trial_end.isoformat() if sub.trial_end else None,
                'trial_days_remaining': sub.trial_days_remaining,
                'in_grace_period': sub.in_grace_period,
                'grace_period_end': sub.grace_period_end.isoformat() if sub.grace_period_end else None,
                'stripe_customer_id': bool(sub.stripe_customer_id),
                'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None,
                'limits': {
                    'max_jobs': sub.plan.max_jobs if sub.plan else 5,
                    'max_candidates': sub.plan.max_candidates if sub.plan else 100,
                    'max_users': sub.plan.max_users if sub.plan else 3,
                } if sub.plan else {},
            })
        except Exception:
            return Response({'status': 'unknown', 'plan': None, 'trial_days_remaining': 0})


class PlansListView(APIView):
    """GET /api/v1/subscription/plans/ — public, no auth"""
    permission_classes = [AllowAny]

    def get(self, request):
        from .models import Plan
        plans = Plan.objects.filter(is_active=True).order_by('price_monthly')
        return Response([{
            'tier': p.tier,
            'name': p.name,
            'price_monthly': str(p.price_monthly),
            'price_annually': str(p.price_annually),
            'max_jobs': p.max_jobs,
            'max_candidates': p.max_candidates,
            'max_users': p.max_users,
            'features': p.features,
        } for p in plans])


class SubscriptionUpgradeView(APIView):
    """POST /api/v1/subscription/upgrade/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .models import Plan
        tier = request.data.get('tier')
        if not tier:
            return Response({'error': 'tier required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            plan = Plan.objects.get(tier=tier, is_active=True)
        except Plan.DoesNotExist:
            return Response({'error': 'Invalid plan'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sub = request.tenant.subscription
            sub.plan = plan
            # In production: create Stripe checkout session here
            # For now: activate the subscription
            sub.status = 'active'
            sub.current_period_start = timezone.now()
            sub.current_period_end = timezone.now() + timedelta(days=30)
            sub.save()
            return Response({'status': 'upgraded', 'plan': plan.tier, 'message': f'Upgraded to {plan.name}'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BillingHistoryView(APIView):
    """GET /api/v1/subscription/billing/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = request.tenant.subscription
            history = sub.billing_history.all()[:20]
            return Response([{
                'id': str(h.id),
                'type': h.record_type,
                'status': h.status,
                'amount': str(h.amount),
                'currency': h.currency,
                'description': h.description,
                'created_at': h.created_at.isoformat(),
                'invoice_pdf_url': h.invoice_pdf_url,
            } for h in history])
        except Exception:
            return Response([])


class StripeWebhookView(APIView):
    """POST /api/v1/subscription/stripe-webhook/ — Handle Stripe events"""
    permission_classes = []  # Stripe signs these requests

    def post(self, request):
        import hmac, hashlib
        from django.conf import settings

        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

        if secret:
            try:
                import stripe
                event = stripe.Webhook.construct_event(payload, sig_header, secret)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            import json
            event = json.loads(payload)

        self._handle_event(event)
        return Response({'received': True})

    def _handle_event(self, event):
        from .models import Subscription
        event_type = event.get('type', '')
        data = event.get('data', {}).get('object', {})

        if event_type == 'customer.subscription.updated':
            stripe_id = data.get('id')
            try:
                sub = Subscription.objects.get(stripe_subscription_id=stripe_id)
                stripe_status = data.get('status')
                if stripe_status == 'active':
                    sub.activate()
                elif stripe_status == 'past_due':
                    sub.status = 'past_due'
                    sub.save()
                elif stripe_status in ('canceled', 'unpaid'):
                    sub.status = 'canceled'
                    sub.save()
            except Subscription.DoesNotExist:
                pass

        elif event_type == 'invoice.paid':
            customer_id = data.get('customer')
            try:
                sub = Subscription.objects.get(stripe_customer_id=customer_id)
                sub.activate()
            except Subscription.DoesNotExist:
                pass
