"""Notifications URL routing — Feature 6 routes added."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Core notifications
    path("", views_extra.NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", views.UnreadCountView.as_view(), name="notification-unread-count"),
    path("mark-all-read/", views.NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("mark-read/", views_extra.NotificationMarkReadView.as_view(), name="notification-mark-read-batch"),
    path("clear-read/", views.NotificationClearAllView.as_view(), name="notification-clear-read"),
    path("<uuid:pk>/read/", views.NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("<uuid:pk>/delete/", views.NotificationDeleteView.as_view(), name="notification-delete"),

    # Preferences
    path("preferences/", views_extra.NotificationPreferencesView.as_view(), name="notification-preferences-v2"),

    # Job alerts
    path("alerts/", views_extra.JobAlertListCreateView.as_view(), name="job-alert-list-v2"),
    path("alerts/bundle/", views_extra.SmartAlertBundleView.as_view(), name="job-alert-bundle"),
    path("alerts/analytics/", views_extra.AlertAnalyticsView.as_view(), name="job-alert-analytics"),
    path("alerts/<uuid:pk>/", views_extra.JobAlertDetailView.as_view(), name="job-alert-detail-v2"),
    path("alerts/<uuid:pk>/toggle/", views_extra.AlertToggleView.as_view(), name="job-alert-toggle-v2"),

    # Push token
    path("push-token/", views_extra.PushTokenRegisterView.as_view(), name="push-token-register"),

    # New since last visit
    path("new-since-last-visit/", views_extra.NewSinceLastVisitView.as_view(), name="new-since-last-visit"),
]
