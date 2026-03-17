"""CampusOS — Internships URLs."""

from django.urls import path
from .views import (
    ExperientialProgramListView,
    InternshipApplicationDetailView,
    InternshipApplicationListCreateView,
    InternshipLogbookListCreateView,
    InternshipOpportunityDetailView,
    InternshipOpportunityListView,
    InternshipOpportunityManageView,
    InternshipRecordDetailView,
    InternshipRecordListCreateView,
    SupervisorEvaluationListCreateView,
)

urlpatterns = [
    # Student browse
    path("opportunities/", InternshipOpportunityListView.as_view(), name="internship-opportunities"),
    # Staff manage
    path("manage/opportunities/", InternshipOpportunityManageView.as_view(), name="internship-manage"),
    path("manage/opportunities/<uuid:pk>/", InternshipOpportunityDetailView.as_view(), name="internship-manage-detail"),
    # Applications
    path("applications/", InternshipApplicationListCreateView.as_view(), name="internship-applications"),
    path("applications/<uuid:pk>/", InternshipApplicationDetailView.as_view(), name="internship-application-detail"),
    # Records
    path("records/", InternshipRecordListCreateView.as_view(), name="internship-records"),
    path("records/<uuid:pk>/", InternshipRecordDetailView.as_view(), name="internship-record-detail"),
    path("records/<uuid:record_id>/logbook/", InternshipLogbookListCreateView.as_view(), name="internship-logbook"),
    path("records/<uuid:record_id>/evaluations/", SupervisorEvaluationListCreateView.as_view(), name="supervisor-evaluations"),
    # Experiential programs
    path("experiential/", ExperientialProgramListView.as_view(), name="experiential-programs"),
]
