"""Jobs URL routing — browse, detail, employer CRUD, saved, similar, report, stats."""
from django.urls import path
from . import views

urlpatterns = [
    # Public browsing
    path("", views.JobListView.as_view(), name="job-list"),
    path("featured/", views.FeaturedJobsView.as_view(), name="job-featured"),
    path("latest/", views.LatestJobsView.as_view(), name="job-latest"),
    path("stats/", views.JobStatsView.as_view(), name="job-stats"),
    path("detail/<slug:slug>/", views.JobDetailView.as_view(), name="job-detail"),
    path("<uuid:pk>/similar/", views.SimilarJobsView.as_view(), name="job-similar"),
    path("<uuid:pk>/company-jobs/", views.OtherCompanyJobsView.as_view(), name="job-company-jobs"),
    path("<uuid:pk>/report/", views.ReportJobView.as_view(), name="job-report"),

    # Saved jobs
    path("saved/", views.SavedJobListView.as_view(), name="saved-job-list"),
    path("saved/<uuid:pk>/", views.SavedJobToggleView.as_view(), name="saved-job-toggle"),

    # Employer job management
    path("employer/", views.EmployerJobListView.as_view(), name="employer-job-list"),
    path("employer/<uuid:pk>/", views.EmployerJobDetailView.as_view(), name="employer-job-detail"),
    path("employer/<uuid:pk>/publish/", views.JobPublishView.as_view(), name="employer-job-publish"),
    path("employer/<uuid:pk>/close/", views.JobCloseView.as_view(), name="employer-job-close"),
]
