"""Marketplace Analytics — URLs (Features 16 & 17)."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("liquidity/", views.MarketplaceLiquidityView.as_view(), name="ma-liquidity"),
    path("funnel/", views.FunnelStatsView.as_view(), name="ma-funnel"),
    path("employer-roi/", views.EmployerROIView.as_view(), name="ma-employer-roi"),
    path("employer-roi/<int:employer_id>/", views.EmployerROIView.as_view(), name="ma-employer-roi-admin"),
    path("health/", views.MarketplaceHealthView.as_view(), name="ma-health"),

    # Feature 16 — Marketplace Analytics & Growth Intelligence
    path("supply-demand/", views_extra.SupplyDemandDashboardView.as_view(), name="ma-supply-demand"),
    path("funnel/detail/", views_extra.ConversionFunnelView.as_view(), name="ma-funnel-detail"),
    path("alert-engagement/", views_extra.AlertEngagementView.as_view(), name="ma-alert-engagement"),
    path("fraud-dashboard/", views_extra.FraudAbuseDashboardView.as_view(), name="ma-fraud-dashboard"),
    path("city-liquidity/", views_extra.CityLiquidityDashboardView.as_view(), name="ma-city-liquidity"),
    path("cohort-retention/", views_extra.CohortRetentionView.as_view(), name="ma-cohort-retention"),
    path("ltv/", views_extra.LTVByEmployerTypeView.as_view(), name="ma-ltv"),
    path("cac/", views_extra.CACByChannelView.as_view(), name="ma-cac"),
    path("candidate-engagement/", views_extra.CandidateEngagementScoringView.as_view(), name="ma-candidate-engagement"),
    path("health-dashboard/", views_extra.MarketplaceHealthDashboardView.as_view(), name="ma-health-dashboard"),

    # Feature 17 — Employer Analytics & ROI
    path("employer/roi/", views_extra.EmployerROIDashboardView.as_view(), name="ma-employer-roi-v2"),
    path("employer/jobs/", views_extra.EmployerJobPerformanceView.as_view(), name="ma-employer-jobs"),
    path("employer/sources/", views_extra.EmployerSourcePerformanceView.as_view(), name="ma-employer-sources"),
    path("employer/response-sla/", views_extra.EmployerResponseSLAView.as_view(), name="ma-employer-sla"),
    path("employer/drop-off/", views_extra.CandidateDropOffAnalyticsView.as_view(), name="ma-employer-dropoff"),
    path("employer/benchmark/", views_extra.EmployerComparativeBenchmarkView.as_view(), name="ma-employer-benchmark"),
    path("employer/review-sentiment/", views_extra.ReviewSentimentTrendView.as_view(), name="ma-employer-sentiment"),
]
