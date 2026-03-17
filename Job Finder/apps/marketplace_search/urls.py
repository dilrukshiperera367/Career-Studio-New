"""Marketplace Search — URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path("feed/", views.PersonalizedFeedView.as_view(), name="ms-personalized-feed"),
    path("similar/<uuid:job_id>/", views.SimilarJobsView.as_view(), name="ms-similar-jobs"),
    path("also-viewed/<uuid:job_id>/", views.AlsoViewedJobsView.as_view(), name="ms-also-viewed"),
    path("role-adjacent/<uuid:job_id>/", views.RoleAdjacentJobsView.as_view(), name="ms-role-adjacent"),
    path("company-recommendations/<int:company_id>/", views.CompanyRecommendationsView.as_view(), name="ms-company-recommendations"),
    path("trending-jobs/", views.TrendingJobsView.as_view(), name="ms-trending-jobs"),
    path("browse/", views.BrowseSurfacesView.as_view(), name="ms-browse-surfaces"),
    path("explain/<uuid:job_id>/", views.SearchExplanationView.as_view(), name="ms-search-explain"),
    path("trending-employers/", views.TrendingEmployersView.as_view(), name="ms-trending-employers"),
]
