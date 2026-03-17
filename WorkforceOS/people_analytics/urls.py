from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AttritionRiskScoreViewSet,
    HeadcountSnapshotViewSet,
    TurnoverReportViewSet,
    DiversityMetricViewSet,
    PeopleAnalyticsReportViewSet,
)

router = DefaultRouter()
router.register('people-analytics/attrition-risk', AttritionRiskScoreViewSet, basename='attrition-risk')
router.register('people-analytics/headcount-snapshots', HeadcountSnapshotViewSet, basename='headcount-snapshots')
router.register('people-analytics/turnover', TurnoverReportViewSet, basename='turnover-reports')
router.register('people-analytics/diversity', DiversityMetricViewSet, basename='diversity-metrics')
router.register('people-analytics/reports', PeopleAnalyticsReportViewSet, basename='people-analytics-reports')

urlpatterns = [
    path('', include(router.urls)),
]
