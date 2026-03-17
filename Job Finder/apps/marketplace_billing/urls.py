"""Marketplace Billing URL routing — Feature 9 routes."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("plans/", views_extra.BillingPlanCatalogueView.as_view(), name="billing-plans-v2"),
    path("subscription/", views.EmployerSubscriptionView.as_view(), name="billing-subscription"),
    path("invoices/", views.InvoiceListView.as_view(), name="billing-invoices"),
    path("wallet/", views.AdBudgetView.as_view(), name="billing-wallet"),
    path("wallet/transactions/", views.AdBudgetTransactionListView.as_view(), name="billing-wallet-txns"),

    # Feature 9 — New
    path("dashboard/", views_extra.SubscriptionDashboardView.as_view(), name="billing-dashboard"),
    path("onboarding/", views_extra.OnboardingWizardView.as_view(), name="billing-onboarding"),
    path("coupon/validate/", views_extra.CouponValidateView.as_view(), name="billing-coupon-validate"),
    path("coupon/apply/", views_extra.CouponApplyView.as_view(), name="billing-coupon-apply"),
    path("wallet/top-up/", views_extra.WalletTopUpView.as_view(), name="billing-wallet-topup"),
    path("job-quality-score/", views_extra.JobAdQualityScoreView.as_view(), name="billing-job-quality"),
    path("fraud-check/", views_extra.FraudRiskCheckView.as_view(), name="billing-fraud-check"),
]
