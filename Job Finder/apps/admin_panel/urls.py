"""Admin Panel URL routing — Feature 20 (Admin, Moderation & Marketplace Operations)."""
from django.urls import path
from . import views_extra

urlpatterns = [
    # Feature 20 — Admin, Moderation & Marketplace Ops
    path("trust-risk/", views_extra.TrustRiskConsoleView.as_view(), name="ops-trust-risk"),
    path("review-moderation/", views_extra.ReviewModerationConsoleView.as_view(), name="ops-review-moderation"),
    path("review-moderation/action/", views_extra.ReviewModerationConsoleView.as_view(), name="ops-review-action"),
    path("employer-verification/", views_extra.EmployerVerificationQueueView.as_view(), name="ops-employer-verification"),
    path("employer-verification/action/", views_extra.EmployerVerificationQueueView.as_view(), name="ops-employer-verification-action"),
    path("job-quality-queue/", views_extra.JobQualityReviewQueueView.as_view(), name="ops-job-quality"),
    path("job-quality-queue/action/", views_extra.JobQualityReviewQueueView.as_view(), name="ops-job-quality-action"),
    path("fraud-investigations/", views_extra.FraudInvestigationView.as_view(), name="ops-fraud"),
    path("billing-disputes/", views_extra.BillingDisputeConsoleView.as_view(), name="ops-billing-disputes"),
    path("billing-disputes/resolve/", views_extra.BillingDisputeConsoleView.as_view(), name="ops-billing-resolve"),
    path("seo-indexation/", views_extra.SEOIndexationMonitorView.as_view(), name="ops-seo"),
    path("search-tuning/", views_extra.SearchTuningConsoleView.as_view(), name="ops-search-tuning"),
    path("search-tuning/synonyms/", views_extra.SearchTuningConsoleView.as_view(), name="ops-synonyms"),
    path("ranking-experiments/", views_extra.RankingExperimentView.as_view(), name="ops-ranking-experiments"),
    path("ranking-experiments/<str:exp_id>/", views_extra.RankingExperimentView.as_view(), name="ops-ranking-experiment-detail"),
    path("feature-flags/", views_extra.FeatureFlagView.as_view(), name="ops-feature-flags"),
    path("feature-flags/<str:flag_key>/", views_extra.FeatureFlagView.as_view(), name="ops-feature-flag-detail"),
    path("bans/", views_extra.BanManagementView.as_view(), name="ops-bans"),
    path("bans/<str:ban_id>/", views_extra.BanManagementView.as_view(), name="ops-ban-detail"),
    path("support-tickets/", views_extra.SupportTicketConsoleView.as_view(), name="ops-support-tickets"),
    path("audit-logs/", views_extra.AuditLogView.as_view(), name="ops-audit-logs"),
    path("legal-requests/", views_extra.LegalRequestHandlerView.as_view(), name="ops-legal-requests"),
]
