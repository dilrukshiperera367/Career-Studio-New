"""CampusOS — Campus Employers views."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsPlacementOfficer
from .models import CampusEmployer, EmployerEngagementLog, EmployerMOU, EmployerSatisfactionSurvey, RecruiterContact
from .serializers import (
    CampusEmployerDetailSerializer,
    CampusEmployerListSerializer,
    EmployerEngagementLogSerializer,
    EmployerMOUSerializer,
    EmployerSatisfactionSurveySerializer,
    RecruiterContactSerializer,
)


class CampusEmployerListView(generics.ListAPIView):
    """Students browse verified employer partners."""
    serializer_class = CampusEmployerListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["engagement_status", "partner_tier", "is_verified"]
    search_fields = ["name", "industry", "hq_city"]
    ordering_fields = ["name", "total_hires"]

    def get_queryset(self):
        return CampusEmployer.objects.filter(campus=self.request.user.campus, is_active=True)


class CampusEmployerManageView(generics.ListCreateAPIView):
    """Staff CRM view of all employer accounts."""
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["engagement_status", "partner_tier"]
    search_fields = ["name", "industry"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CampusEmployerDetailSerializer
        return CampusEmployerListSerializer

    def get_queryset(self):
        return CampusEmployer.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)


class CampusEmployerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CampusEmployerDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return CampusEmployer.objects.filter(campus=self.request.user.campus)


class RecruiterContactListCreateView(generics.ListCreateAPIView):
    serializer_class = RecruiterContactSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return RecruiterContact.objects.filter(employer_id=self.kwargs["employer_id"])

    def perform_create(self, serializer):
        employer = get_object_or_404(CampusEmployer, id=self.kwargs["employer_id"])
        serializer.save(employer=employer)


class EmployerEngagementLogView(generics.ListCreateAPIView):
    serializer_class = EmployerEngagementLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return EmployerEngagementLog.objects.filter(employer_id=self.kwargs["employer_id"])

    def perform_create(self, serializer):
        employer = get_object_or_404(CampusEmployer, id=self.kwargs["employer_id"])
        serializer.save(employer=employer, logged_by=self.request.user)


class EmployerMOUListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployerMOUSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return EmployerMOU.objects.filter(employer_id=self.kwargs["employer_id"])

    def perform_create(self, serializer):
        employer = get_object_or_404(CampusEmployer, id=self.kwargs["employer_id"])
        serializer.save(employer=employer)
