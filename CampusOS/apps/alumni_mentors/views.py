"""CampusOS — Alumni Mentors views."""

from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsAlumniMentor, IsStudent
from .models import AlumniJobShare, GroupMentoringCircle, MentorRequest, MentorSession, MentorshipGoal, AlumniProfile
from .serializers import (
    AlumniJobShareSerializer,
    AlumniProfileDetailSerializer,
    AlumniProfileListSerializer,
    GroupMentoringCircleSerializer,
    MentorRequestSerializer,
    MentorSessionSerializer,
    MentorshipGoalSerializer,
)


class AlumniMentorBrowseView(generics.ListAPIView):
    """Students browse available mentors."""
    serializer_class = AlumniProfileListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["current_industry", "graduation_year", "preferred_meeting_mode"]
    search_fields = ["mentoring_areas", "current_employer", "current_designation"]
    ordering_fields = ["mentor_rating", "total_sessions_completed"]

    def get_queryset(self):
        return AlumniProfile.objects.filter(
            campus=self.request.user.campus, is_mentor=True, is_verified=True
        )


class AlumniProfileMeView(generics.RetrieveUpdateAPIView):
    """Alumni manage their own profile."""
    serializer_class = AlumniProfileDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsAlumniMentor]

    def get_object(self):
        return self.request.user.alumni_profile


class MentorRequestListCreateView(generics.ListCreateAPIView):
    """A student requests/lists their mentorship requests."""
    serializer_class = MentorRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "alumni_mentor":
            return MentorRequest.objects.filter(mentor__user=user)
        return MentorRequest.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class MentorRequestDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = MentorRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "alumni_mentor":
            return MentorRequest.objects.filter(mentor__user=user)
        return MentorRequest.objects.filter(student=user)


class MentorSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = MentorSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MentorSession.objects.filter(mentorship_id=self.kwargs["mentorship_id"])

    def perform_create(self, serializer):
        serializer.save(mentorship_id=self.kwargs["mentorship_id"])


class MentorshipGoalListCreateView(generics.ListCreateAPIView):
    serializer_class = MentorshipGoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MentorshipGoal.objects.filter(mentorship_id=self.kwargs["mentorship_id"])

    def perform_create(self, serializer):
        serializer.save(mentorship_id=self.kwargs["mentorship_id"])


class GroupCircleListCreateView(generics.ListCreateAPIView):
    serializer_class = GroupMentoringCircleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "topic_tags"]

    def get_queryset(self):
        return GroupMentoringCircle.objects.filter(campus=self.request.user.campus, is_public=True)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, host=self.request.user.alumni_profile)


class AlumniJobShareListCreateView(generics.ListCreateAPIView):
    serializer_class = AlumniJobShareSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["opportunity_type", "is_active"]
    search_fields = ["title", "company"]

    def get_queryset(self):
        return AlumniJobShare.objects.filter(campus=self.request.user.campus, is_active=True)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, shared_by=self.request.user.alumni_profile)
