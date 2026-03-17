"""CampusOS — Outcomes Analytics views."""

from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsPlacementOfficer
from .models import AccreditationReport, AlumniDestination, CohortOutcome, EmployabilityTrendPoint, PlacementOutcome
from .serializers import (
    AccreditationReportSerializer,
    AlumniDestinationSerializer,
    CohortOutcomeSerializer,
    EmployabilityTrendPointSerializer,
    PlacementOutcomeSerializer,
)


class PlacementOutcomeListView(generics.ListAPIView):
    """Placement officer browses all outcomes for their campus."""
    serializer_class = PlacementOutcomeSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["outcome_type", "is_verified", "academic_year", "program"]

    def get_queryset(self):
        return PlacementOutcome.objects.filter(campus=self.request.user.campus).select_related("student", "program")


class PlacementOutcomeDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PlacementOutcomeSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return PlacementOutcome.objects.filter(campus=self.request.user.campus)


class MyPlacementOutcomeView(generics.RetrieveUpdateAPIView):
    """Students view/update their own outcome."""
    serializer_class = PlacementOutcomeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        outcome, _ = PlacementOutcome.objects.get_or_create(
            student=self.request.user, defaults={"campus": self.request.user.campus}
        )
        return outcome


class CohortOutcomeListView(generics.ListAPIView):
    serializer_class = CohortOutcomeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["academic_year", "department", "program", "is_published"]

    def get_queryset(self):
        return CohortOutcome.objects.filter(campus=self.request.user.campus)


class AccreditationReportListCreateView(generics.ListCreateAPIView):
    serializer_class = AccreditationReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return AccreditationReport.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, generated_by=self.request.user)


class EmployabilityTrendView(generics.ListAPIView):
    serializer_class = EmployabilityTrendPointSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["program"]

    def get_queryset(self):
        return EmployabilityTrendPoint.objects.filter(campus=self.request.user.campus).order_by("-as_of_date")[:90]
