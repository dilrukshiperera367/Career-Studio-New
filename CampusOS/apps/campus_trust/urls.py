from django.urls import path
from . import views

urlpatterns = [
    path("employer-verifications/", views.EmployerVerificationListView.as_view(), name="employer-verification-list"),
    path("employer-verifications/<uuid:pk>/", views.EmployerVerificationDetailView.as_view(), name="employer-verification-detail"),
    path("opportunity-flags/", views.SuspiciousOpportunityFlagCreateView.as_view(), name="opportunity-flags"),
    path("abuse-reports/", views.AbuseReportCreateView.as_view(), name="abuse-reports"),
    path("trust-score/me/", views.TrustScoreMeView.as_view(), name="trust-score-me"),
]
