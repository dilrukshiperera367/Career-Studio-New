"""ATS Connector URL routing — Features 18 (ATS Bridge 2.0)."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("connection/", views.ATSConnectionView.as_view(), name="ats-connection"),
    path("setup/", views.ATSConnectionSetupView.as_view(), name="ats-setup"),
    path("webhook/", views.WebhookReceiveView.as_view(), name="ats-webhook"),
    path("webhook/logs/", views.WebhookLogListView.as_view(), name="ats-webhook-logs"),
    path("sync/records/", views.SyncRecordListView.as_view(), name="ats-sync-records"),
    path("sync/trigger/", views.TriggerSyncView.as_view(), name="ats-trigger-sync"),

    # Feature 18 — ATS Bridge 2.0
    path("normalize/", views_extra.FeedNormalizationView.as_view(), name="ats-normalize"),
    path("feed-quality/", views_extra.FeedQualityValidationView.as_view(), name="ats-feed-quality"),
    path("dedup/", views_extra.DedupCrossATSView.as_view(), name="ats-dedup"),
    path("consent-check/", views_extra.CandidateConsentCheckView.as_view(), name="ats-consent-check"),
    path("sync/apply-status/", views_extra.ApplyStatusSyncView.as_view(), name="ats-apply-status-sync"),
    path("sync/interviews/", views_extra.InterviewSyncView.as_view(), name="ats-interview-sync"),
    path("sync/offers/", views_extra.OfferStatusSyncView.as_view(), name="ats-offer-sync"),
    path("sync/dispositions/", views_extra.DispositionSyncView.as_view(), name="ats-disposition-sync"),
    path("sync/close-expire/", views_extra.CloseExpireSyncView.as_view(), name="ats-close-expire-sync"),
    path("error-console/", views_extra.ErrorReplayConsoleView.as_view(), name="ats-error-console"),
    path("webhook/replay/", views_extra.WebhookReplayView.as_view(), name="ats-webhook-replay"),
    path("webhook/diagnostics/", views_extra.WebhookDiagnosticsView.as_view(), name="ats-webhook-diagnostics"),
    path("partners/", views_extra.ATSPartnerMarketplaceView.as_view(), name="ats-partners"),
]
