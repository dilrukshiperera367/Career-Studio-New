"""CampusOS — Placements URLs."""

from django.urls import path
from .views import (
    AcceptOfferView,
    DriveOfferListCreateView,
    DriveSlotListCreateView,
    PlacementDriveDetailView,
    PlacementDriveListView,
    PlacementDriveManageView,
    PlacementSeasonDetailView,
    PlacementSeasonListCreateView,
    ShortlistStudentView,
    StudentDriveRegistrationListView,
)

urlpatterns = [
    path("seasons/", PlacementSeasonListCreateView.as_view(), name="placement-seasons"),
    path("seasons/<uuid:pk>/", PlacementSeasonDetailView.as_view(), name="placement-season-detail"),
    path("drives/", PlacementDriveListView.as_view(), name="placement-drives"),
    path("manage/drives/", PlacementDriveManageView.as_view(), name="placement-drives-manage"),
    path("manage/drives/<uuid:pk>/", PlacementDriveDetailView.as_view(), name="placement-drive-detail"),
    path("manage/drives/<uuid:drive_id>/registrations/", StudentDriveRegistrationListView.as_view(), name="drive-registrations"),
    path("manage/drives/<uuid:drive_id>/slots/", DriveSlotListCreateView.as_view(), name="drive-slots"),
    path("registrations/", StudentDriveRegistrationListView.as_view(), name="my-registrations"),
    path("registrations/<uuid:registration_id>/shortlist/", ShortlistStudentView.as_view(), name="shortlist-student"),
    path("offers/", DriveOfferListCreateView.as_view(), name="drive-offers"),
    path("offers/<uuid:pk>/accept/", AcceptOfferView.as_view(), name="accept-offer"),
]
