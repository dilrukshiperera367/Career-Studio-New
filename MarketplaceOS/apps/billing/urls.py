from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProviderPlanViewSet, ProviderSubscriptionViewSet,
    MarketplaceCommissionConfigViewSet, BookingCommissionViewSet,
    FeaturedListingProductViewSet, FeaturedListingPurchaseViewSet,
    EnterpriseBudgetViewSet, EnterpriseBudgetTransactionViewSet,
    CoachingBundleViewSet,
)

router = DefaultRouter()
router.register(r"provider-plans", ProviderPlanViewSet, basename="provider-plan")
router.register(r"provider-subscriptions", ProviderSubscriptionViewSet, basename="provider-subscription")
router.register(r"commission-configs", MarketplaceCommissionConfigViewSet, basename="commission-config")
router.register(r"booking-commissions", BookingCommissionViewSet, basename="booking-commission")
router.register(r"featured-listing-products", FeaturedListingProductViewSet, basename="featured-listing-product")
router.register(r"featured-listing-purchases", FeaturedListingPurchaseViewSet, basename="featured-listing-purchase")
router.register(r"enterprise-budgets-billing", EnterpriseBudgetViewSet, basename="enterprise-budget-billing")
router.register(r"enterprise-budget-transactions", EnterpriseBudgetTransactionViewSet, basename="enterprise-budget-transaction")
router.register(r"coaching-bundles", CoachingBundleViewSet, basename="coaching-bundle")

urlpatterns = [
    path("", include(router.urls)),
]
