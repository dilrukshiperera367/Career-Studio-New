"""URL configuration for consent app."""

from django.urls import path
from apps.consent.views import (
    ConsentRecordView,
    CandidateSelfConsentView,
    ConsentSummaryView,
    DataRequestView,
    DataRequestDetailView,
)

urlpatterns = [
    # Consent management (tenant admin / recruiter)
    path("", ConsentRecordView.as_view(), name="consent-list"),
    path("summary/", ConsentSummaryView.as_view(), name="consent-summary"),
    # Self-service consent for candidates (career portal)
    path("self/", CandidateSelfConsentView.as_view(), name="consent-self"),
    # GDPR data requests
    path("data-requests/", DataRequestView.as_view(), name="data-requests"),
    path("data-requests/<uuid:request_id>/", DataRequestDetailView.as_view(), name="data-request-detail"),
]
