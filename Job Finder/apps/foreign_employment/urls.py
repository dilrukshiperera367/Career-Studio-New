"""Foreign Employment URL routing."""
from django.urls import path
from . import views

urlpatterns = [
    path("agencies/", views.AgencyListView.as_view(), name="agency-list"),
    path("agencies/<slug:slug>/", views.AgencyDetailView.as_view(), name="agency-detail"),
    path("agencies/<slug:slug>/jobs/", views.AgencyJobsView.as_view(), name="agency-jobs"),
    path("jobs/", views.OverseasJobListView.as_view(), name="overseas-job-list"),
    path("jobs/<uuid:pk>/", views.OverseasJobDetailView.as_view(), name="overseas-job-detail"),
    path("countries/", views.CountryListView.as_view(), name="country-list"),
    path("checklist/", views.PreDepartureChecklistView.as_view(), name="predeparture-checklist"),
    path("checklist/<str:country>/", views.PreDepartureChecklistView.as_view(), name="predeparture-checklist-country"),
]
