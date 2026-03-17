from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/student/", views.StudentDashboardStatsView.as_view(), name="student-dashboard-stats"),
    path("dashboard/officer/", views.PlacementOfficerDashboardView.as_view(), name="officer-dashboard-stats"),
    path("programs/placement/", views.ProgramPlacementStatsView.as_view(), name="program-placement-stats"),
]
