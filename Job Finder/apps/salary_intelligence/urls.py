"""Salary Intelligence URL routing — Feature 8 routes."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("estimate/", views.SalaryEstimateView.as_view(), name="sal-estimate"),
    path("benchmark/", views.SalaryBenchmarkView.as_view(), name="sal-benchmark"),
    path("trend/", views.SalaryTrendView.as_view(), name="sal-trend"),
    path("submit/", views.SalarySubmissionView.as_view(), name="sal-submit"),
    path("company/<slug:slug>/", views.CompanySalaryView.as_view(), name="sal-company"),
    path("cost-of-living/", views.CostOfLivingView.as_view(), name="sal-col"),

    # Feature 8 — New
    path("guide/", views_extra.SalaryGuideView.as_view(), name="sal-guide"),
    path("guide/", views_extra.SalaryGuideView.as_view(), name="sal-guide"),
    path("total-comp/", views_extra.TotalCompensationView.as_view(), name="sal-total-comp"),
    path("compare/", views_extra.CompensationCompareView.as_view(), name="sal-compare"),
    path("skill-pay/", views_extra.SkillPayView.as_view(), name="sal-skill-pay"),
    path("shift-pay/", views_extra.ShiftPayComparisonView.as_view(), name="sal-shift-pay"),
    path("submit-verified/", views_extra.SalarySubmitView.as_view(), name="sal-submit-verified"),
    path("transparency/<slug:slug>/", views_extra.PayTransparencyScoreView.as_view(), name="sal-transparency"),
    path("company/<slug:slug>/salaries/", views_extra.CompanySalaryPageView.as_view(), name="sal-company-salaries"),
]
