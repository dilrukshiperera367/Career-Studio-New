from django.urls import path
from . import views

urlpatterns = [
    path("outcomes/", views.PlacementOutcomeListView.as_view(), name="outcome-list"),
    path("outcomes/me/", views.MyPlacementOutcomeView.as_view(), name="outcome-me"),
    path("outcomes/<uuid:pk>/", views.PlacementOutcomeDetailView.as_view(), name="outcome-detail"),
    path("cohorts/", views.CohortOutcomeListView.as_view(), name="cohort-outcomes"),
    path("accreditation/", views.AccreditationReportListCreateView.as_view(), name="accreditation-reports"),
    path("trends/", views.EmployabilityTrendView.as_view(), name="employability-trends"),
]
