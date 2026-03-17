"""Moderation URL routing — reports, moderation actions, employer verification."""
from django.urls import path
from . import views

urlpatterns = [
    path("reports/", views.ReportListView.as_view(), name="report-list"),
    path("reports/create/", views.ReportCreateView.as_view(), name="report-create"),
    path("reports/<uuid:pk>/", views.ReportDetailView.as_view(), name="report-detail"),
    path("reports/<uuid:pk>/resolve/", views.ReportResolveView.as_view(), name="report-resolve"),
    path("actions/", views.ModerationActionListView.as_view(), name="moderation-action-list"),
    path("employer-verification/", views.EmployerVerificationQueueView.as_view(), name="employer-verification-queue"),
    path("employer-verification/<uuid:pk>/", views.EmployerVerificationActionView.as_view(), name="employer-verification-action"),
]
