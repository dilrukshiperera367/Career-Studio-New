from django.urls import path
from . import views

urlpatterns = [
    path("", views.AssessmentBundleListView.as_view(), name="assessment-list"),
    path("manage/", views.AssessmentBundleManageView.as_view(), name="assessment-manage"),
    path("<uuid:pk>/", views.AssessmentBundleDetailView.as_view(), name="assessment-detail"),
    path("schedules/", views.AssessmentScheduleListCreateView.as_view(), name="assessment-schedules"),
    path("my-attempts/", views.MyAssessmentAttemptsView.as_view(), name="my-attempts"),
    path("benchmarks/", views.CampusBenchmarkView.as_view(), name="benchmarks"),
]
