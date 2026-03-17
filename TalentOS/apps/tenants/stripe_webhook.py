"""Stripe webhook handler for ATS tenant subscriptions."""
import stripe
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from apps.accounts.models import Subscription

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            logger.warning('Stripe webhook: invalid payload')
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.warning('Stripe webhook: invalid signature')
            return HttpResponse(status=400)

        event_type = event['type']
        data = event['data']['object']

        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(data)
        elif event_type == 'invoice.payment_succeeded':
            _handle_payment_succeeded(data)
        elif event_type == 'invoice.payment_failed':
            _handle_payment_failed(data)
        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_deleted(data)
        elif event_type == 'customer.subscription.updated':
            _handle_subscription_updated(data)
        else:
            logger.debug('Stripe webhook: unhandled event %s', event_type)

        return HttpResponse(status=200)


def _handle_checkout_completed(session):
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')
    if not customer_id:
        return
    try:
        sub = Subscription.objects.get(stripe_customer_id=customer_id)
        sub.stripe_subscription_id = subscription_id or sub.stripe_subscription_id
        sub.status = 'active'
        sub.save(update_fields=['stripe_subscription_id', 'status'])
        logger.info('Subscription activated for customer %s', customer_id)
    except Subscription.DoesNotExist:
        logger.warning('No subscription found for customer %s', customer_id)


def _handle_payment_succeeded(invoice):
    customer_id = invoice.get('customer')
    if not customer_id:
        return
    try:
        sub = Subscription.objects.get(stripe_customer_id=customer_id)
        if sub.status not in ('active',):
            sub.status = 'active'
            sub.save(update_fields=['status'])
        logger.info('Payment succeeded for customer %s', customer_id)
    except Subscription.DoesNotExist:
        logger.warning('No subscription found for customer %s', customer_id)


def _handle_payment_failed(invoice):
    customer_id = invoice.get('customer')
    if not customer_id:
        return
    try:
        sub = Subscription.objects.get(stripe_customer_id=customer_id)
        sub.status = 'past_due'
        sub.save(update_fields=['status'])
        logger.warning('Payment failed for customer %s — subscription past_due', customer_id)
    except Subscription.DoesNotExist:
        logger.warning('No subscription found for customer %s', customer_id)


def _handle_subscription_deleted(stripe_sub):
    sub_id = stripe_sub.get('id')
    if not sub_id:
        return
    try:
        sub = Subscription.objects.get(stripe_subscription_id=sub_id)
        sub.status = 'cancelled'
        sub.save(update_fields=['status'])
        logger.info('Subscription cancelled: %s', sub_id)
    except Subscription.DoesNotExist:
        logger.warning('No subscription found for stripe_subscription_id %s', sub_id)


def _handle_subscription_updated(stripe_sub):
    sub_id = stripe_sub.get('id')
    stripe_status = stripe_sub.get('status', '')
    if not sub_id:
        return
    status_map = {
        'active': 'active',
        'past_due': 'past_due',
        'canceled': 'cancelled',
        'unpaid': 'past_due',
        'trialing': 'trial',
    }
    local_status = status_map.get(stripe_status)
    if not local_status:
        return
    try:
        sub = Subscription.objects.get(stripe_subscription_id=sub_id)
        sub.status = local_status
        sub.save(update_fields=['status'])
        logger.info('Subscription %s status → %s', sub_id, local_status)
    except Subscription.DoesNotExist:
        logger.warning('No subscription found for stripe_subscription_id %s', sub_id)
