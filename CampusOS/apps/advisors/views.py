from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsFacultyOrAdvisor, IsPlacementOfficer
from .models import AdvisorProfile, AdvisorStudentMapping, InterventionAlert, ResumeApprovalRequest, StudentNote
from .serializers import (
    AdvisorProfileSerializer,
    AdvisorStudentMappingSerializer,
    InterventionAlertSerializer,
    ResumeApprovalRequestSerializer,
    StudentNoteSerializer,
)


class AdvisorProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = AdvisorProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]

    def get_object(self):
        return self.request.user.advisor_profile


class MyCaseloadView(generics.ListAPIView):
    """Advisor views their student caseload."""
    serializer_class = AdvisorStudentMappingSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]

    def get_queryset(self):
        return AdvisorStudentMapping.objects.filter(
            advisor__user=self.request.user, is_active=True
        ).select_related("student")


class StudentNoteListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentNoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["note_type", "is_flagged"]

    def get_queryset(self):
        return StudentNote.objects.filter(
            advisor__user=self.request.user, student_id=self.kwargs["student_id"]
        )

    def perform_create(self, serializer):
        serializer.save(advisor=self.request.user.advisor_profile, student_id=self.kwargs["student_id"])


class ResumeApprovalListView(generics.ListAPIView):
    """Advisor views resume submissions pending their review."""
    serializer_class = ResumeApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_queryset(self):
        return ResumeApprovalRequest.objects.filter(advisor__user=self.request.user)


class ResumeApprovalDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ResumeApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]

    def get_queryset(self):
        return ResumeApprovalRequest.objects.filter(advisor__user=self.request.user)


class MyResumeApprovalView(generics.ListCreateAPIView):
    """Student submits resume for approval."""
    serializer_class = ResumeApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ResumeApprovalRequest.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class InterventionAlertListView(generics.ListCreateAPIView):
    serializer_class = InterventionAlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["alert_type", "severity", "status"]

    def get_queryset(self):
        return InterventionAlert.objects.filter(assigned_to__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InterventionAlertDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InterventionAlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]

    def get_queryset(self):
        return InterventionAlert.objects.filter(assigned_to__user=self.request.user)
