from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsPlacementOfficer
from .models import AssessmentBundle, AssessmentSchedule, CampusBenchmarkScore, StudentAssessmentAttempt
from .serializers import (
    AssessmentBundleSerializer,
    AssessmentScheduleSerializer,
    CampusBenchmarkScoreSerializer,
    StudentAssessmentAttemptSerializer,
)


class AssessmentBundleListView(generics.ListAPIView):
    serializer_class = AssessmentBundleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AssessmentBundle.objects.filter(campus=self.request.user.campus, is_active=True)


class AssessmentBundleManageView(generics.ListCreateAPIView):
    serializer_class = AssessmentBundleSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return AssessmentBundle.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, created_by=self.request.user)


class AssessmentBundleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AssessmentBundleSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return AssessmentBundle.objects.filter(campus=self.request.user.campus)


class AssessmentScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = AssessmentScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return AssessmentSchedule.objects.filter(bundle__campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save()


class MyAssessmentAttemptsView(generics.ListAPIView):
    serializer_class = StudentAssessmentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_queryset(self):
        return StudentAssessmentAttempt.objects.filter(student=self.request.user)


class CampusBenchmarkView(generics.ListAPIView):
    serializer_class = CampusBenchmarkScoreSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["bundle", "program"]

    def get_queryset(self):
        return CampusBenchmarkScore.objects.filter(bundle__campus=self.request.user.campus)
