from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SavedProviderViewSet, SavedServiceViewSet, ProviderComparisonViewSet,
    BuyerProfileViewSet, MatchRequestViewSet, MarketplaceSearchView,
)

router = DefaultRouter()
router.register(r"saved-providers", SavedProviderViewSet, basename="saved-provider")
router.register(r"saved-services", SavedServiceViewSet, basename="saved-service")
router.register(r"comparisons", ProviderComparisonViewSet, basename="comparison")
router.register(r"buyer-profiles", BuyerProfileViewSet, basename="buyer-profile")
router.register(r"match-requests", MatchRequestViewSet, basename="match-request")
router.register(r"search", MarketplaceSearchView, basename="search")

urlpatterns = [
    path("", include(router.urls)),
]
