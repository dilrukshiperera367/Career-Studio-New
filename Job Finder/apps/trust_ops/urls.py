"""Trust Ops URL routing — Feature 11 routes."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("strikes/", views.StrikeListView.as_view(), name="trust-strikes"),
    path("suspend/", views.SuspendUserView.as_view(), name="trust-suspend"),
    path("risk-score/<int:employer_id>/", views.RiskScoreView.as_view(), name="trust-risk-score"),
    path("report-phishing/", views.PhishingReportView.as_view(), name="trust-phishing"),
    path("scam-alerts/", views.ScamAlertListView.as_view(), name="trust-scam-alerts"),

    # Feature 11 — Trust Score
    path("trust-score/employer/<slug:slug>/", views_extra.EmployerTrustScoreView.as_view(), name="trust-score-employer"),
    path("reputation/<slug:slug>/history/", views_extra.EmployerReputationHistoryView.as_view(), name="trust-reputation"),

    # Feature 11 — Fraud & Safety Detection
    path("detect-suspicious-job/", views_extra.SuspiciousJobDetectionView.as_view(), name="trust-detect-suspicious"),
    path("detect-duplicate-job/", views_extra.DuplicateJobDetectionView.as_view(), name="trust-detect-duplicate"),
    path("detect-bot-application/", views_extra.BotApplicationDetectionView.as_view(), name="trust-detect-bot"),

    # Feature 11 — Report Flow
    path("report/", views_extra.UnifiedReportView.as_view(), name="trust-report"),
    path("report/<uuid:report_id>/status/", views_extra.ReportStatusView.as_view(), name="trust-report-status"),

    # Feature 11 — Scam Warning Banners
    path("scam-warning/job/<uuid:job_id>/", views_extra.ScamWarningBannerView.as_view(), name="trust-scam-warning-job"),
    path("scam-warning/employer/<slug:slug>/", views_extra.EmployerScamWarningView.as_view(), name="trust-scam-warning-employer"),

    # Feature 11 — Verification & Moderation
    path("employer-verify/submit/", views_extra.EmployerVerificationSubmitView.as_view(), name="trust-employer-verify"),
    path("moderation-queue/", views_extra.ModerationQueueOverviewView.as_view(), name="trust-moderation-queue"),
]
