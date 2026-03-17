"""Agency Analytics URL configuration."""
from rest_framework.routers import DefaultRouter
from .views import (
    DailyKPISnapshotViewSet, RecruiterPerformanceViewSet,
    ClientAnalyticsViewSet, FunnelMetricsViewSet,
)

router = DefaultRouter()
router.register("kpi-snapshots", DailyKPISnapshotViewSet, basename="kpi-snapshot")
router.register("recruiter-performance", RecruiterPerformanceViewSet, basename="recruiter-performance")
router.register("client-analytics", ClientAnalyticsViewSet, basename="client-analytics")
router.register("funnel-metrics", FunnelMetricsViewSet, basename="funnel-metrics")

urlpatterns = router.urls
