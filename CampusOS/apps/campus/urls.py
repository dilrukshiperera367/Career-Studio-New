"""CampusOS — Campus URLs."""

from django.urls import path
from .views import (
    AcademicYearListCreateView,
    CampusBranchListCreateView,
    CampusDetailView,
    CampusListView,
    CampusUpdateView,
    DepartmentDetailView,
    DepartmentListCreateView,
    ProgramDetailView,
    ProgramListCreateView,
)

urlpatterns = [
    path("", CampusListView.as_view(), name="campus-list"),
    path("<slug:slug>/", CampusDetailView.as_view(), name="campus-detail"),
    path("my/settings/", CampusUpdateView.as_view(), name="campus-settings"),
    path("my/departments/", DepartmentListCreateView.as_view(), name="department-list"),
    path("my/departments/<uuid:pk>/", DepartmentDetailView.as_view(), name="department-detail"),
    path("my/programs/", ProgramListCreateView.as_view(), name="program-list"),
    path("my/programs/<uuid:pk>/", ProgramDetailView.as_view(), name="program-detail"),
    path("my/academic-years/", AcademicYearListCreateView.as_view(), name="academic-year-list"),
    path("my/branches/", CampusBranchListCreateView.as_view(), name="branch-list"),
]
