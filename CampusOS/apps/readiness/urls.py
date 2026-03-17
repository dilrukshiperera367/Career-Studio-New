"""CampusOS — Readiness URLs."""

from django.urls import path
from .views import (
    CompetencyListView,
    CompetencyScoreCreateView,
    ImprovementPlanDetailView,
    ImprovementPlanListCreateView,
    ImprovementPlanTaskListCreateView,
    MyReadinessAssessmentsView,
    PlacementRiskFlagDetailView,
    PlacementRiskFlagListView,
    ReadinessAssessmentCreateView,
    ReadinessAssessmentDetailView,
    ReadinessBenchmarkView,
    SubmitAssessmentView,
    WeeklyCareerActionListCreateView,
)

urlpatterns = [
    path("competencies/", CompetencyListView.as_view(), name="competency-list"),
    path("assessments/", MyReadinessAssessmentsView.as_view(), name="readiness-assessments"),
    path("assessments/create/", ReadinessAssessmentCreateView.as_view(), name="readiness-create"),
    path("assessments/<uuid:pk>/", ReadinessAssessmentDetailView.as_view(), name="readiness-detail"),
    path("assessments/<uuid:pk>/submit/", SubmitAssessmentView.as_view(), name="readiness-submit"),
    path("assessments/<uuid:assessment_id>/scores/", CompetencyScoreCreateView.as_view(), name="competency-score"),
    path("plans/", ImprovementPlanListCreateView.as_view(), name="improvement-plans"),
    path("plans/<uuid:pk>/", ImprovementPlanDetailView.as_view(), name="improvement-plan-detail"),
    path("plans/<uuid:plan_id>/tasks/", ImprovementPlanTaskListCreateView.as_view(), name="improvement-tasks"),
    path("weekly-actions/", WeeklyCareerActionListCreateView.as_view(), name="weekly-actions"),
    path("risk-flags/", PlacementRiskFlagListView.as_view(), name="risk-flags"),
    path("risk-flags/<uuid:pk>/", PlacementRiskFlagDetailView.as_view(), name="risk-flag-detail"),
    path("benchmarks/", ReadinessBenchmarkView.as_view(), name="readiness-benchmarks"),
]
