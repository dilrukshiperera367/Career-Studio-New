from django.urls import path
from apps.tenants.views import TenantDetailView, TenantSettingsView, SubscriptionView, TrialStatusView
from .stripe_webhook import StripeWebhookView
from .billing_views import CreateCheckoutSessionView, BillingPortalView, CancelSubscriptionView, SubscriptionStatusView

urlpatterns = [
    path("current/", TenantDetailView.as_view(), name="tenant-detail"),
    path("settings/", TenantSettingsView.as_view(), name="tenant-settings"),
    path("subscription/", SubscriptionView.as_view(), name="tenant-subscription"),
    path("trial-status/", TrialStatusView.as_view(), name="tenant-trial-status"),
    path('webhook/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('billing/checkout/', CreateCheckoutSessionView.as_view(), name='billing-checkout'),
    path('billing/portal/', BillingPortalView.as_view(), name='billing-portal'),
    path('billing/cancel/', CancelSubscriptionView.as_view(), name='billing-cancel'),
    path('billing/status/', SubscriptionStatusView.as_view(), name='billing-status'),
]
