from rest_framework import generics, permissions
from apps.shared.permissions import IsPlacementOfficer
from .models import AbuseReport, AlumniVerification, EmployerVerification, SuspiciousOpportunityFlag, TrustScore
from .serializers import (
    AbuseReportSerializer,
    AlumniVerificationSerializer,
    EmployerVerificationSerializer,
    SuspiciousOpportunityFlagSerializer,
    TrustScoreSerializer,
)


class EmployerVerificationListView(generics.ListAPIView):
    serializer_class = EmployerVerificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return EmployerVerification.objects.filter(employer__campus=self.request.user.campus)


class EmployerVerificationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = EmployerVerificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return EmployerVerification.objects.filter(employer__campus=self.request.user.campus)


class SuspiciousOpportunityFlagCreateView(generics.ListCreateAPIView):
    serializer_class = SuspiciousOpportunityFlagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("campus_admin", "placement_officer", "super_admin"):
            return SuspiciousOpportunityFlag.objects.filter(status__in=["open", "investigating"])
        return SuspiciousOpportunityFlag.objects.filter(flagged_by=user)

    def perform_create(self, serializer):
        serializer.save(flagged_by=self.request.user)


class AbuseReportCreateView(generics.CreateAPIView):
    serializer_class = AbuseReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)


class TrustScoreMeView(generics.RetrieveAPIView):
    serializer_class = TrustScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        score, _ = TrustScore.objects.get_or_create(user=self.request.user)
        return score
