"""Analytics URL routing — platform stats, employer dashboard, top searches."""
from django.urls import path
from . import views

urlpatterns = [
    path("platform/", views.PlatformStatsView.as_view(), name="platform-stats"),
    path("employer/", views.EmployerDashboardAnalyticsView.as_view(), name="employer-analytics"),
    path("top-searches/", views.TopSearchTermsView.as_view(), name="top-searches"),
]
