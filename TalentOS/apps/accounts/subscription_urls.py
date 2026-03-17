from django.urls import path
from . import subscription_views

urlpatterns = [
    path('status/', subscription_views.SubscriptionStatusView.as_view(), name='subscription-status'),
    path('plans/', subscription_views.PlansListView.as_view(), name='plans-list'),
    path('upgrade/', subscription_views.SubscriptionUpgradeView.as_view(), name='subscription-upgrade'),
    path('billing/', subscription_views.BillingHistoryView.as_view(), name='billing-history'),
    path('stripe-webhook/', subscription_views.StripeWebhookView.as_view(), name='stripe-webhook'),
]
