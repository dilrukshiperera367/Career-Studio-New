"""CampusOS — Campus views."""

from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import AcademicYear, Campus, CampusBranch, Department, Program
from .serializers import (
    AcademicYearSerializer,
    CampusBranchSerializer,
    CampusDetailSerializer,
    CampusListSerializer,
    DepartmentSerializer,
    ProgramSerializer,
)
from apps.shared.permissions import IsCampusAdmin, IsSameCampus


class CampusListView(generics.ListAPIView):
    """List campuses — public endpoint for institution discovery."""
    queryset = Campus.objects.filter(is_active=True)
    serializer_class = CampusListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "short_name", "city", "country"]
    ordering_fields = ["name", "created_at"]


class CampusDetailView(generics.RetrieveAPIView):
    queryset = Campus.objects.filter(is_active=True)
    serializer_class = CampusDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


class CampusUpdateView(generics.RetrieveUpdateAPIView):
    """Campus admin update."""
    serializer_class = CampusDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_object(self):
        return self.request.user.campus


class DepartmentListCreateView(generics.ListCreateAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsSameCampus]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Department.objects.filter(campus=self.request.user.campus, is_active=True)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_queryset(self):
        return Department.objects.filter(campus=self.request.user.campus)


class ProgramListCreateView(generics.ListCreateAPIView):
    serializer_class = ProgramSerializer
    permission_classes = [permissions.IsAuthenticated, IsSameCampus]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["department", "degree_type", "is_active"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Program.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)


class ProgramDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProgramSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_queryset(self):
        return Program.objects.filter(campus=self.request.user.campus)


class AcademicYearListCreateView(generics.ListCreateAPIView):
    serializer_class = AcademicYearSerializer
    permission_classes = [permissions.IsAuthenticated, IsSameCampus]

    def get_queryset(self):
        return AcademicYear.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)


class CampusBranchListCreateView(generics.ListCreateAPIView):
    serializer_class = CampusBranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsSameCampus]

    def get_queryset(self):
        return CampusBranch.objects.filter(campus=self.request.user.campus, is_active=True)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)
