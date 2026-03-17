"""CampusOS — Students URLs."""

from django.urls import path
from .views import (
    CampusReadinessBadgeListView,
    EmployabilityProfileView,
    IssueCampusReadinessBadgeView,
    MyStudentProfileView,
    StudentActivityLogView,
    StudentAchievementDetailView,
    StudentAchievementListCreateView,
    StudentCertificationDetailView,
    StudentCertificationListCreateView,
    StudentEducationDetailView,
    StudentEducationListCreateView,
    StudentLanguageDetailView,
    StudentLanguageListCreateView,
    StudentProfileDetailStaffView,
    StudentProfileListView,
    StudentProjectDetailView,
    StudentProjectListCreateView,
    StudentSkillDetailView,
    StudentSkillListCreateView,
)

urlpatterns = [
    # Student self-service
    path("me/", MyStudentProfileView.as_view(), name="student-profile-me"),
    path("me/employability/", EmployabilityProfileView.as_view(), name="student-employability"),
    path("me/skills/", StudentSkillListCreateView.as_view(), name="student-skills"),
    path("me/skills/<uuid:pk>/", StudentSkillDetailView.as_view(), name="student-skill-detail"),
    path("me/education/", StudentEducationListCreateView.as_view(), name="student-education"),
    path("me/education/<uuid:pk>/", StudentEducationDetailView.as_view(), name="student-education-detail"),
    path("me/projects/", StudentProjectListCreateView.as_view(), name="student-projects"),
    path("me/projects/<uuid:pk>/", StudentProjectDetailView.as_view(), name="student-project-detail"),
    path("me/certifications/", StudentCertificationListCreateView.as_view(), name="student-certifications"),
    path("me/certifications/<uuid:pk>/", StudentCertificationDetailView.as_view(), name="student-certification-detail"),
    path("me/languages/", StudentLanguageListCreateView.as_view(), name="student-languages"),
    path("me/languages/<uuid:pk>/", StudentLanguageDetailView.as_view(), name="student-language-detail"),
    path("me/achievements/", StudentAchievementListCreateView.as_view(), name="student-achievements"),
    path("me/achievements/<uuid:pk>/", StudentAchievementDetailView.as_view(), name="student-achievement-detail"),
    path("me/activity/", StudentActivityLogView.as_view(), name="student-activity"),
    path("me/badges/", CampusReadinessBadgeListView.as_view(), name="student-badges"),
    # Staff views
    path("", StudentProfileListView.as_view(), name="student-list"),
    path("<uuid:pk>/", StudentProfileDetailStaffView.as_view(), name="student-detail"),
    path("<uuid:student_id>/badges/issue/", IssueCampusReadinessBadgeView.as_view(), name="issue-badge"),
]
