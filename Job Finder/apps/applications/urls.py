"""Applications URL routing — all Feature 5 routes added."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # ── Seeker — core ─────────────────────────────────────────────────────────
    path("apply/", views.ApplyView.as_view(), name="application-apply"),
    path("draft/", views.SaveDraftApplicationView.as_view(), name="application-draft"),
    path("my/", views.MyApplicationsView.as_view(), name="my-applications"),
    path("my/<uuid:pk>/", views.MyApplicationDetailView.as_view(), name="my-application-detail"),
    path("my/<uuid:pk>/withdraw/", views.WithdrawApplicationView.as_view(), name="application-withdraw"),
    path("my/<uuid:pk>/submit-draft/", views.SubmitDraftView.as_view(), name="application-submit-draft"),
    path("my/<uuid:pk>/notes/", views.ApplicationNoteListCreateView.as_view(), name="application-notes"),
    path("my/notes/<uuid:pk>/", views.ApplicationNoteDetailView.as_view(), name="application-note-detail"),

    # ── Seeker — Feature 5 ────────────────────────────────────────────────────
    path("quick-apply/", views_extra.QuickApplyView.as_view(), name="application-quick-apply"),
    path("batch-apply/", views_extra.BatchApplyView.as_view(), name="application-batch-apply"),
    path("analytics/", views_extra.SeekerApplicationAnalyticsView.as_view(), name="application-analytics"),
    path("nudges/", views_extra.NudgeListView.as_view(), name="application-nudges"),
    path("nudges/<uuid:pk>/dismiss/", views_extra.NudgeDismissView.as_view(), name="nudge-dismiss"),
    path("my/<uuid:pk>/tasks/", views_extra.ApplicationTaskListCreateView.as_view(), name="application-tasks"),
    path("my/<uuid:pk>/tasks/<uuid:id>/", views_extra.ApplicationTaskDetailView.as_view(), name="application-task-detail"),
    path("my/<uuid:pk>/withdrawal-reason/", views_extra.WithdrawalReasonView.as_view(), name="application-withdrawal-reason"),

    path("reapply/<uuid:job_id>/eligibility/", views_extra.ReapplyEligibilityView.as_view(), name="reapply-eligibility"),
    path("employer-response-rate/<uuid:employer_id>/", views_extra.EmployerResponseRateView.as_view(), name="employer-response-rate"),

    # External tracker
    path("external/", views_extra.ExternalApplicationListCreateView.as_view(), name="external-applications"),
    path("external/<uuid:pk>/", views_extra.ExternalApplicationDetailView.as_view(), name="external-application-detail"),

    # ── Seeker — interviews ───────────────────────────────────────────────────
    path("my/interviews/", views.SeekerInterviewListView.as_view(), name="my-interviews"),
    path("my/interviews/<uuid:pk>/confirm/", views.ConfirmInterviewView.as_view(), name="interview-confirm"),

    # ── Seeker — offers ───────────────────────────────────────────────────────
    path("my/<uuid:pk>/offer/", views.OfferDetailView.as_view(), name="my-offer"),
    path("my/<uuid:pk>/offer/respond/", views.RespondToOfferView.as_view(), name="offer-respond"),

    # ── Employer ──────────────────────────────────────────────────────────────
    path("employer/", views.EmployerApplicationsView.as_view(), name="employer-applications"),
    path("employer/<uuid:pk>/", views.EmployerApplicationDetailView.as_view(), name="employer-application-detail"),
    path("employer/<uuid:pk>/status/", views.UpdateApplicationStatusView.as_view(), name="application-status-update"),
    path("employer/<uuid:pk>/history/", views.ApplicationStatusHistoryView.as_view(), name="application-status-history"),
    path("employer/<uuid:pk>/interviews/", views.InterviewListCreateView.as_view(), name="employer-interviews"),
    path("employer/interviews/<uuid:pk>/", views.InterviewDetailView.as_view(), name="employer-interview-detail"),
    path("employer/<uuid:pk>/offer/", views.CreateOfferView.as_view(), name="create-offer"),
]
