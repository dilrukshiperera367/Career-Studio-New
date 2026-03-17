"""Stripe billing service for HRM tenant subscriptions."""
import stripe
import logging
from django.conf import settings
from .models import Tenant
from .enterprise import Subscription

logger = logging.getLogger(__name__)


def get_or_create_stripe_customer(tenant: Tenant, admin_email: str) -> str:
    """Get or create a Stripe customer for the tenant."""
    sub = getattr(tenant, 'subscription', None)
    if sub and sub.stripe_customer_id:
        return sub.stripe_customer_id

    customer = stripe.Customer.create(
        email=admin_email,
        name=tenant.name,
        metadata={'tenant_id': str(tenant.id), 'subdomain': tenant.slug},
    )
    if sub:
        sub.stripe_customer_id = customer.id
        sub.save(update_fields=['stripe_customer_id'])
    return customer.id


def create_checkout_session(tenant: Tenant, admin_email: str, price_id: str,
                             success_url: str, cancel_url: str) -> dict:
    """Create a Stripe Checkout session for subscription upgrade."""
    customer_id = get_or_create_stripe_customer(tenant, admin_email)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'tenant_id': str(tenant.id)},
        allow_promotion_codes=True,
    )
    return {'checkout_url': session.url, 'session_id': session.id}


def create_billing_portal_session(tenant: Tenant, return_url: str) -> dict:
    """Create a Stripe Customer Portal session for managing subscription."""
    sub = getattr(tenant, 'subscription', None)
    if not sub or not sub.stripe_customer_id:
        raise ValueError('No Stripe customer found for this tenant.')
    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )
    return {'portal_url': session.url}


def cancel_subscription(tenant: Tenant) -> bool:
    """Cancel subscription at period end."""
    sub = getattr(tenant, 'subscription', None)
    if not sub or not sub.stripe_subscription_id:
        return False
    stripe.Subscription.modify(
        sub.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    return True
