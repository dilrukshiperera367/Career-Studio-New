"""CampusOS — Students views."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import (
    IsCampusAdmin,
    IsFacultyOrAdvisor,
    IsOwnerOrCampusStaff,
    IsPlacementOfficer,
)
from .models import (
    CampusReadinessBadge,
    EmployabilityProfile,
    StudentActivityLog,
    StudentAchievement,
    StudentCertification,
    StudentEducation,
    StudentLanguage,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from .serializers import (
    CampusReadinessBadgeSerializer,
    EmployabilityProfileSerializer,
    StudentActivityLogSerializer,
    StudentAchievementSerializer,
    StudentCertificationSerializer,
    StudentEducationSerializer,
    StudentLanguageSerializer,
    StudentProfileDetailSerializer,
    StudentProfileSerializer,
    StudentProjectSerializer,
    StudentSkillSerializer,
)


class MyStudentProfileView(generics.RetrieveUpdateAPIView):
    """Student's own profile — GET and PATCH."""
    serializer_class = StudentProfileDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = StudentProfile.objects.get_or_create(
            user=self.request.user,
            defaults={"campus_id": self.request.user.campus_id},
        )
        return profile


class StudentProfileListView(generics.ListAPIView):
    """Staff/placement view of all student profiles on campus."""
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "program", "department", "current_year", "placement_eligibility",
        "show_to_employers", "profile_public",
    ]
    search_fields = [
        "user__first_name", "user__last_name", "user__email",
        "student_id", "specialization",
    ]
    ordering_fields = ["created_at", "cgpa", "current_year"]

    def get_queryset(self):
        return StudentProfile.objects.filter(
            campus=self.request.user.campus
        ).select_related("user", "program", "department")


class StudentProfileDetailStaffView(generics.RetrieveAPIView):
    """Staff view of a specific student profile."""
    serializer_class = StudentProfileDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]

    def get_queryset(self):
        return StudentProfile.objects.filter(campus=self.request.user.campus)


# ---------- Sub-resource views (student-owned) ----------

class StudentSkillListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentSkillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentSkill.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=profile)


class StudentSkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StudentSkillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentSkill.objects.filter(student__user=self.request.user)


class StudentEducationListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentEducationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentEducation.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=profile)


class StudentEducationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StudentEducationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentEducation.objects.filter(student__user=self.request.user)


class StudentProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentProject.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=profile)


class StudentProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StudentProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentProject.objects.filter(student__user=self.request.user)


class StudentCertificationListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentCertificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentCertification.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=profile)


class StudentCertificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StudentCertificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentCertification.objects.filter(student__user=self.request.user)


class StudentLanguageListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentLanguageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentLanguage.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=profile)


class StudentLanguageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StudentLanguageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentLanguage.objects.filter(student__user=self.request.user)


class StudentAchievementListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentAchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentAchievement.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=profile)


class StudentAchievementDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StudentAchievementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentAchievement.objects.filter(student__user=self.request.user)


class EmployabilityProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = EmployabilityProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        ep, _ = EmployabilityProfile.objects.get_or_create(student=profile)
        return ep


class StudentActivityLogView(generics.ListAPIView):
    serializer_class = StudentActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentActivityLog.objects.filter(student__user=self.request.user)


class CampusReadinessBadgeListView(generics.ListAPIView):
    serializer_class = CampusReadinessBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CampusReadinessBadge.objects.filter(student__user=self.request.user)


class IssueCampusReadinessBadgeView(generics.CreateAPIView):
    """Staff issue a readiness badge to a student."""
    serializer_class = CampusReadinessBadgeSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]

    def perform_create(self, serializer):
        student_id = self.kwargs["student_id"]
        student = get_object_or_404(
            StudentProfile,
            id=student_id,
            campus=self.request.user.campus,
        )
        serializer.save(student=student, issued_by=self.request.user)
