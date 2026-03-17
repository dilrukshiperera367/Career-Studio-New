"""Search URL routing — job search, company search, suggestions, trending, analytics."""
from django.urls import path
from . import views

urlpatterns = [
    path("jobs/", views.JobSearchView.as_view(), name="search-jobs"),
    path("companies/", views.CompanySearchView.as_view(), name="search-companies"),
    path("suggestions/", views.SearchSuggestionsView.as_view(), name="search-suggestions"),
    path("trending/", views.TrendingSearchesView.as_view(), name="search-trending"),
    path("recent/", views.RecentSearchesView.as_view(), name="search-recent"),
    path("analytics/", views.SearchAnalyticsView.as_view(), name="search-analytics"),
]
