from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ManagerDashboardConfigViewSet, TeamAlertViewSet, OneOnOneViewSet,
    CoachingNoteViewSet, TeamPerformanceSummaryViewSet, DelegationRuleViewSet,
    TeamRosterViewViewSet, TeamAttendanceSnapshotViewSet, ApprovalItemViewSet,
    OnboardingOffboardingTrackerViewSet, SkillGapSummaryViewSet, FlightRiskAlertViewSet,
    SuccessionPlanEntryViewSet, CompPlanningWorkspaceViewSet, RecognitionActionViewSet,
    TrainingCompletionViewViewSet, WorkforceCostSnapshotViewSet,
    ScheduleCoverageAlertViewSet, ActionRecommendationViewSet,
)

router = DefaultRouter()
router.register(r'manager/dashboard-config', ManagerDashboardConfigViewSet, basename='manager-dashboard-config')
router.register(r'manager/team-alerts', TeamAlertViewSet, basename='team-alerts')
router.register(r'manager/one-on-ones', OneOnOneViewSet, basename='one-on-ones')
router.register(r'manager/coaching-notes', CoachingNoteViewSet, basename='coaching-notes')
router.register(r'manager/team-performance', TeamPerformanceSummaryViewSet, basename='team-performance')
router.register(r'manager/delegations', DelegationRuleViewSet, basename='delegations')
# Feature 3 new routes
router.register(r'manager/team-roster', TeamRosterViewViewSet, basename='team-roster')
router.register(r'manager/attendance-snapshots', TeamAttendanceSnapshotViewSet, basename='attendance-snapshots')
router.register(r'manager/approvals', ApprovalItemViewSet, basename='approval-items')
router.register(r'manager/ob-ob-trackers', OnboardingOffboardingTrackerViewSet, basename='ob-ob-trackers')
router.register(r'manager/skill-gaps', SkillGapSummaryViewSet, basename='skill-gaps')
router.register(r'manager/flight-risks', FlightRiskAlertViewSet, basename='flight-risks')
router.register(r'manager/succession-plans', SuccessionPlanEntryViewSet, basename='succession-plans')
router.register(r'manager/comp-planning', CompPlanningWorkspaceViewSet, basename='comp-planning')
router.register(r'manager/recognition', RecognitionActionViewSet, basename='recognition')
router.register(r'manager/training-compliance', TrainingCompletionViewViewSet, basename='training-compliance')
router.register(r'manager/workforce-cost', WorkforceCostSnapshotViewSet, basename='workforce-cost')
router.register(r'manager/coverage-alerts', ScheduleCoverageAlertViewSet, basename='coverage-alerts')
router.register(r'manager/recommendations', ActionRecommendationViewSet, basename='recommendations')

urlpatterns = [
    path('', include(router.urls)),
]

