"""Mobile API URL routing — Feature 14: Mobile-First."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("register-token/", views.RegisterPushTokenView.as_view(), name="mobile-register-token"),
    path("token/", views.RegisterPushTokenView.as_view(), name="mobile-delete-token"),
    path("preferences/", views.DevicePreferenceView.as_view(), name="mobile-preferences"),
    path("feed/", views.MobileJobFeedView.as_view(), name="mobile-feed"),

    # Feature 14 — Push Notifications
    path("push/send/", views_extra.SendPushNotificationView.as_view(), name="mobile-push-send"),
    path("interview-reminder/", views_extra.InterviewReminderSetView.as_view(), name="mobile-interview-reminder"),

    # Feature 14 — Commute & Save
    path("commute-feed/", views_extra.CommuteAwareJobFeedView.as_view(), name="mobile-commute-feed"),
    path("save-job/<uuid:job_id>/", views_extra.OneTapSaveJobView.as_view(), name="mobile-save-job"),

    # Feature 14 — Voice Search
    path("voice-search/", views_extra.VoiceSearchView.as_view(), name="mobile-voice-search"),

    # Feature 14 — Device Preferences (per-device)
    path("device-preferences/<str:device_id>/", views_extra.DevicePreferenceUpdateView.as_view(), name="mobile-device-pref"),

    # Feature 14 — Session Analytics
    path("session/", views_extra.MobileSessionLogView.as_view(), name="mobile-session-log"),
    path("analytics/funnel/", views_extra.MobileAnalyticsFunnelView.as_view(), name="mobile-funnel"),

    # Feature 14 — Low-Bandwidth Feed
    path("lb-feed/", views_extra.LowBandwidthJobFeedView.as_view(), name="mobile-lb-feed"),

    # Feature 14 — Document Scanner
    path("document-scanner/submit/", views_extra.DocumentScannerSubmitView.as_view(), name="mobile-doc-scanner"),
]
