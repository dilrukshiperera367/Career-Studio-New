from rest_framework import generics, permissions, filters
from apps.shared.permissions import IsPlacementOfficer
from .models import DigitalBadge, MicroCredential, MicroCredentialEnrollment, SkillEvidenceBundle, StudentBadgeAward, VerifiedCertification
from .serializers import (
    DigitalBadgeSerializer,
    MicroCredentialEnrollmentSerializer,
    MicroCredentialSerializer,
    SkillEvidenceBundleSerializer,
    StudentBadgeAwardSerializer,
    VerifiedCertificationSerializer,
)


class DigitalBadgeListView(generics.ListAPIView):
    serializer_class = DigitalBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DigitalBadge.objects.filter(campus=self.request.user.campus, is_active=True)


class DigitalBadgeManageView(generics.ListCreateAPIView):
    serializer_class = DigitalBadgeSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return DigitalBadge.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, created_by=self.request.user)


class MyBadgesView(generics.ListAPIView):
    serializer_class = StudentBadgeAwardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentBadgeAward.objects.filter(student=self.request.user, is_revoked=False)


class MyVerifiedCertificationsView(generics.ListCreateAPIView):
    serializer_class = VerifiedCertificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VerifiedCertification.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user, campus=self.request.user.campus)


class MicroCredentialListView(generics.ListAPIView):
    serializer_class = MicroCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "skill_domain"]

    def get_queryset(self):
        return MicroCredential.objects.filter(campus=self.request.user.campus, is_active=True)


class MyMicroCredentialEnrollmentsView(generics.ListCreateAPIView):
    serializer_class = MicroCredentialEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MicroCredentialEnrollment.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class MySkillBundlesView(generics.ListCreateAPIView):
    serializer_class = SkillEvidenceBundleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SkillEvidenceBundle.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
