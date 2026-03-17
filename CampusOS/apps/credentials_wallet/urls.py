from django.urls import path
from . import views

urlpatterns = [
    path("badges/", views.DigitalBadgeListView.as_view(), name="badge-list"),
    path("badges/manage/", views.DigitalBadgeManageView.as_view(), name="badge-manage"),
    path("my-badges/", views.MyBadgesView.as_view(), name="my-badges"),
    path("my-certifications/", views.MyVerifiedCertificationsView.as_view(), name="my-certifications"),
    path("micro-credentials/", views.MicroCredentialListView.as_view(), name="micro-credential-list"),
    path("my-enrollments/", views.MyMicroCredentialEnrollmentsView.as_view(), name="my-mc-enrollments"),
    path("skill-bundles/", views.MySkillBundlesView.as_view(), name="skill-bundles"),
]
