"""CampusOS — Campus Employers URLs."""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.CampusEmployerListView.as_view(), name="employer-list"),
    path("manage/", views.CampusEmployerManageView.as_view(), name="employer-manage"),
    path("<uuid:pk>/", views.CampusEmployerDetailView.as_view(), name="employer-detail"),
    path("<uuid:employer_id>/recruiters/", views.RecruiterContactListCreateView.as_view(), name="recruiter-list"),
    path("<uuid:employer_id>/logs/", views.EmployerEngagementLogView.as_view(), name="engagement-logs"),
    path("<uuid:employer_id>/mou/", views.EmployerMOUListCreateView.as_view(), name="employer-mou"),
]
