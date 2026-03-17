"""AI Governance URL routing."""
from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.DashboardStatsView.as_view(), name="governance-dashboard"),
    path("decisions/", views.AIDecisionLogListView.as_view(), name="decision-log-list"),
    path("decisions/<uuid:pk>/", views.AIDecisionLogDetailView.as_view(), name="decision-log-detail"),
    path("decisions/<uuid:pk>/review/", views.AIDecisionReviewView.as_view(), name="decision-review"),
    path("bias-metrics/", views.BiasMetricListView.as_view(), name="bias-metric-list"),
    path("guardrails/", views.GuardrailListView.as_view(), name="guardrail-list"),
    path("guardrails/<uuid:pk>/toggle/", views.GuardrailToggleView.as_view(), name="guardrail-toggle"),
]
