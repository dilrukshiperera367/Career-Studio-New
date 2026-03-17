"""Assessments URL routing."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.AssessmentListView.as_view(), name="assessment-list"),
    path("<uuid:pk>/", views.AssessmentDetailView.as_view(), name="assessment-detail"),
    path("<uuid:pk>/start/", views.StartAssessmentView.as_view(), name="assessment-start"),
    path("attempts/<uuid:attempt_id>/submit/", views.SubmitAssessmentView.as_view(), name="assessment-submit"),
    path("my/attempts/", views.MyAssessmentAttemptsView.as_view(), name="my-attempts"),
    path("my/attempts/<uuid:pk>/result/", views.AssessmentResultView.as_view(), name="attempt-result"),
]
