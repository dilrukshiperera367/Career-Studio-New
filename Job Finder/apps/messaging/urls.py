"""Messaging URL routing — Feature 13: Comms 2.0."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("threads/", views.ThreadListView.as_view(), name="thread-list"),
    path("threads/create/", views.ThreadCreateView.as_view(), name="thread-create"),
    path("threads/<uuid:pk>/", views.ThreadDetailView.as_view(), name="thread-detail"),
    path("threads/<uuid:pk>/messages/", views.MessageListView.as_view(), name="message-list"),
    path("threads/<uuid:pk>/send/", views.SendMessageView.as_view(), name="message-send"),
    path("threads/<uuid:pk>/read/", views.MarkThreadReadView.as_view(), name="thread-mark-read"),

    # Feature 13 — Message Request Inbox
    path("requests/", views_extra.MessageRequestInboxView.as_view(), name="msg-requests"),

    # Feature 13 — Templates
    path("templates/", views_extra.MessageTemplateListView.as_view(), name="msg-templates"),
    path("templates/render/", views_extra.MessageTemplateRenderView.as_view(), name="msg-template-render"),

    # Feature 13 — Anti-Phishing
    path("scan-phishing/", views_extra.MessagePhishingScanView.as_view(), name="msg-scan-phishing"),

    # Feature 13 — Interview Scheduling
    path("threads/<uuid:thread_id>/schedule-interview/", views_extra.InterviewScheduleInThreadView.as_view(), name="msg-schedule-interview"),

    # Feature 13 — Categorization
    path("threads/<uuid:thread_id>/categorize/", views_extra.MessageCategorizationView.as_view(), name="msg-categorize"),

    # Feature 13 — Follow-Up & SLA
    path("follow-up-suggestions/", views_extra.FollowUpSuggestionsView.as_view(), name="msg-follow-up"),

    # Feature 13 — Analytics
    path("analytics/", views_extra.MessageAnalyticsView.as_view(), name="msg-analytics"),

    # Feature 13 — Archive / Spam
    path("threads/<uuid:thread_id>/archive/", views_extra.ThreadArchiveView.as_view(), name="msg-archive"),

    # Feature 13 — Verified Sender
    path("verified-sender/<uuid:user_id>/", views_extra.VerifiedSenderInfoView.as_view(), name="msg-verified-sender"),
]
