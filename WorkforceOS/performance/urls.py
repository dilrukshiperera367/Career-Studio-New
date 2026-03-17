"""Performance URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .goal_views import GoalAnalyticsView, TeamGoalsSummaryView

router = DefaultRouter()
router.register(r'performance/cycles', views.ReviewCycleViewSet, basename='review-cycle')
router.register(r'performance/reviews', views.PerformanceReviewViewSet, basename='performance-review')
router.register(r'goals', views.GoalViewSet, basename='goal')
router.register(r'feedback', views.FeedbackViewSet, basename='feedback')
# P1 upgrades
router.register(r'performance/talent-reviews', views.TalentReviewViewSet, basename='talent-review')
router.register(r'performance/nine-box', views.NineBoxPlacementViewSet, basename='nine-box')
router.register(r'performance/succession-plans', views.SuccessionPlanViewSet, basename='succession-plan')
router.register(r'performance/succession-candidates', views.SuccessionCandidateViewSet, basename='succession-candidate')
router.register(r'performance/promotion-readiness', views.PromotionReadinessViewSet, basename='promotion-readiness')

urlpatterns = [
    path('', include(router.urls)),
    path('performance/goals/analytics/', GoalAnalyticsView.as_view(), name='goal-analytics'),
    path('performance/goals/team-summary/', TeamGoalsSummaryView.as_view(), name='team-goal-summary'),
]
