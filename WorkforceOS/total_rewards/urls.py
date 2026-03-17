from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    CompensationBandViewSet,
    MeritCycleViewSet,
    MeritRecommendationViewSet,
    EquityGrantViewSet,
    TotalRewardsStatementViewSet,
    PayEquityAnalysisViewSet,
    BonusIncentivePlanViewSet,
    BonusIncentiveEntryViewSet,
    ManagerCompReviewWorkspaceViewSet,
    CompChangeApprovalViewSet,
)

router = DefaultRouter()
router.register(r'rewards/comp-bands', CompensationBandViewSet, basename='comp-bands')
router.register(r'rewards/merit-cycles', MeritCycleViewSet, basename='merit-cycles')
router.register(r'rewards/merit-recommendations', MeritRecommendationViewSet, basename='merit-recommendations')
router.register(r'rewards/equity-grants', EquityGrantViewSet, basename='equity-grants')
router.register(r'rewards/statements', TotalRewardsStatementViewSet, basename='trs')
router.register(r'rewards/pay-equity', PayEquityAnalysisViewSet, basename='pay-equity')
# Feature 5 upgrades
router.register(r'rewards/bonus-plans', BonusIncentivePlanViewSet, basename='bonus-plans')
router.register(r'rewards/bonus-entries', BonusIncentiveEntryViewSet, basename='bonus-entries')
router.register(r'rewards/comp-review-workspaces', ManagerCompReviewWorkspaceViewSet, basename='comp-review-workspaces')
router.register(r'rewards/comp-change-approvals', CompChangeApprovalViewSet, basename='comp-change-approvals')

urlpatterns = [
    path('', include(router.urls)),
]
