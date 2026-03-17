from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MarketplaceSnapshotViewSet, ProviderAnalyticsViewSet,
    SearchEventViewSet, BookingFunnelEventViewSet, ProviderViewEventViewSet,
)

router = DefaultRouter()
router.register(r"marketplace-snapshots", MarketplaceSnapshotViewSet, basename="marketplace-snapshot")
router.register(r"provider-analytics", ProviderAnalyticsViewSet, basename="provider-analytics")
router.register(r"search-events", SearchEventViewSet, basename="search-event")
router.register(r"funnel-events", BookingFunnelEventViewSet, basename="funnel-event")
router.register(r"provider-view-events", ProviderViewEventViewSet, basename="provider-view-event")

urlpatterns = [
    path("", include(router.urls)),
]
