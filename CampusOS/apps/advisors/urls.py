from django.urls import path
from . import views

urlpatterns = [
    path("profile/me/", views.AdvisorProfileMeView.as_view(), name="advisor-profile-me"),
    path("caseload/", views.MyCaseloadView.as_view(), name="advisor-caseload"),
    path("students/<uuid:student_id>/notes/", views.StudentNoteListCreateView.as_view(), name="student-notes"),
    path("resume-reviews/", views.ResumeApprovalListView.as_view(), name="resume-reviews"),
    path("resume-reviews/<uuid:pk>/", views.ResumeApprovalDetailView.as_view(), name="resume-review-detail"),
    path("resume-reviews/my/", views.MyResumeApprovalView.as_view(), name="my-resume-reviews"),
    path("interventions/", views.InterventionAlertListView.as_view(), name="interventions"),
    path("interventions/<uuid:pk>/", views.InterventionAlertDetailView.as_view(), name="intervention-detail"),
]
