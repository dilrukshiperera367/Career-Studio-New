from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProviderReportViewSet, DisputeViewSet, QualityScoreViewSet, RiskFlagViewSet, BackgroundCheckViewSet

router = DefaultRouter()
router.register("provider-reports", ProviderReportViewSet, basename="provider-report")
router.register("disputes", DisputeViewSet, basename="dispute")
router.register("quality-scores", QualityScoreViewSet, basename="quality-score")
router.register("risk-flags", RiskFlagViewSet, basename="risk-flag")
router.register("background-checks", BackgroundCheckViewSet, basename="background-check")

urlpatterns = [path("", include(router.urls))]
