"""CampusOS — Alumni Mentors URLs."""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.AlumniMentorBrowseView.as_view(), name="alumni-mentor-browse"),
    path("profile/me/", views.AlumniProfileMeView.as_view(), name="alumni-profile-me"),
    path("requests/", views.MentorRequestListCreateView.as_view(), name="mentor-request-list"),
    path("requests/<uuid:pk>/", views.MentorRequestDetailView.as_view(), name="mentor-request-detail"),
    path("requests/<uuid:mentorship_id>/sessions/", views.MentorSessionListCreateView.as_view(), name="mentor-sessions"),
    path("requests/<uuid:mentorship_id>/goals/", views.MentorshipGoalListCreateView.as_view(), name="mentorship-goals"),
    path("circles/", views.GroupCircleListCreateView.as_view(), name="mentor-circles"),
    path("job-shares/", views.AlumniJobShareListCreateView.as_view(), name="alumni-job-shares"),
]
