"""Feed Normalization — URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path("sources/", views.FeedSourceListView.as_view(), name="fn-sources"),
    path("errors/", views.FeedErrorLogListView.as_view(), name="fn-errors"),
    path("errors/<uuid:error_id>/replay/", views.ReplayFeedErrorView.as_view(), name="fn-replay"),
    path("duplicates/", views.DuplicateDetectionListView.as_view(), name="fn-duplicates"),
]
