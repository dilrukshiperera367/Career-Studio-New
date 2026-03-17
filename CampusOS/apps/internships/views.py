"""CampusOS — Internships views."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsFacultyOrAdvisor, IsPlacementOfficer, IsCampusAdmin
from apps.students.models import StudentProfile
from .models import (
    ExperientialEnrollment,
    ExperientialProgram,
    InternshipApplication,
    InternshipLogbook,
    InternshipOpportunity,
    InternshipRecord,
    SupervisorEvaluation,
    TrainingAgreement,
)
from .serializers import (
    ExperientialEnrollmentSerializer,
    ExperientialProgramSerializer,
    InternshipApplicationSerializer,
    InternshipLogbookSerializer,
    InternshipOpportunitySerializer,
    InternshipRecordSerializer,
    SupervisorEvaluationSerializer,
    TrainingAgreementSerializer,
)


class InternshipOpportunityListView(generics.ListAPIView):
    """Browse available internship opportunities on campus."""
    serializer_class = InternshipOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["opportunity_type", "work_mode", "is_paid", "status"]
    search_fields = ["title", "employer_name", "description"]
    ordering_fields = ["created_at", "application_deadline"]

    def get_queryset(self):
        return InternshipOpportunity.objects.filter(
            campus=self.request.user.campus,
            status=InternshipOpportunity.Status.OPEN,
        )


class InternshipOpportunityManageView(generics.ListCreateAPIView):
    """Staff manage internship opportunities."""
    serializer_class = InternshipOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["opportunity_type", "status"]

    def get_queryset(self):
        return InternshipOpportunity.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, posted_by=self.request.user)


class InternshipOpportunityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InternshipOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return InternshipOpportunity.objects.filter(campus=self.request.user.campus)


class InternshipApplicationListCreateView(generics.ListCreateAPIView):
    """Student applies to internships."""
    serializer_class = InternshipApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("placement_officer", "campus_admin", "faculty_advisor"):
            return InternshipApplication.objects.filter(opportunity__campus=user.campus)
        return InternshipApplication.objects.filter(student__user=user)

    def perform_create(self, serializer):
        student = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=student)


class InternshipApplicationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InternshipApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("placement_officer", "campus_admin", "faculty_advisor"):
            return InternshipApplication.objects.filter(opportunity__campus=user.campus)
        return InternshipApplication.objects.filter(student__user=user)


class InternshipRecordListCreateView(generics.ListCreateAPIView):
    serializer_class = InternshipRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("placement_officer", "campus_admin", "faculty_advisor"):
            return InternshipRecord.objects.filter(campus=user.campus)
        return InternshipRecord.objects.filter(student__user=user)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)


class InternshipRecordDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InternshipRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("placement_officer", "campus_admin"):
            return InternshipRecord.objects.filter(campus=user.campus)
        return InternshipRecord.objects.filter(student__user=user)


class InternshipLogbookListCreateView(generics.ListCreateAPIView):
    serializer_class = InternshipLogbookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InternshipLogbook.objects.filter(
            record__student__user=self.request.user,
            record_id=self.kwargs["record_id"],
        )

    def perform_create(self, serializer):
        record = get_object_or_404(
            InternshipRecord,
            id=self.kwargs["record_id"],
            student__user=self.request.user,
        )
        serializer.save(record=record)


class SupervisorEvaluationListCreateView(generics.ListCreateAPIView):
    serializer_class = SupervisorEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SupervisorEvaluation.objects.filter(record_id=self.kwargs["record_id"])

    def perform_create(self, serializer):
        record = get_object_or_404(InternshipRecord, id=self.kwargs["record_id"])
        serializer.save(record=record)


class ExperientialProgramListView(generics.ListCreateAPIView):
    serializer_class = ExperientialProgramSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["program_type", "is_active"]

    def get_queryset(self):
        return ExperientialProgram.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)
