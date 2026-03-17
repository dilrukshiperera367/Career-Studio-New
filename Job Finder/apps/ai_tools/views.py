"""AI Tools views."""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CoverLetter, LinkedInAnalysis, InterviewPrepSession, InterviewAnswer,
    MentorProfile, MentorshipRequest, NetworkingDraft,
    BrandScore, CareerRoadmap,
)
from .serializers import (
    CoverLetterSerializer, LinkedInAnalysisSerializer,
    InterviewPrepSessionSerializer, InterviewAnswerSerializer,
    MentorProfileSerializer, MentorshipRequestSerializer,
    NetworkingDraftSerializer, BrandScoreSerializer,
    CareerRoadmapSerializer,
)


# ── Cover Letters ─────────────────────────────────────────────────────────────

class CoverLetterListCreateView(generics.ListCreateAPIView):
    serializer_class = CoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CoverLetter.objects.filter(user=self.request.user)


class CoverLetterDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CoverLetter.objects.filter(user=self.request.user)


# ── LinkedIn Analysis ─────────────────────────────────────────────────────────

class LinkedInAnalysisListCreateView(generics.ListCreateAPIView):
    serializer_class = LinkedInAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LinkedInAnalysis.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LinkedInAnalysisDetailView(generics.RetrieveAPIView):
    serializer_class = LinkedInAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LinkedInAnalysis.objects.filter(user=self.request.user)


# ── Interview Prep ────────────────────────────────────────────────────────────

class InterviewSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = InterviewPrepSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InterviewPrepSession.objects.filter(
            user=self.request.user
        ).prefetch_related("answers")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InterviewSessionDetailView(generics.RetrieveAPIView):
    serializer_class = InterviewPrepSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InterviewPrepSession.objects.filter(
            user=self.request.user
        ).prefetch_related("answers")


class InterviewAnswerCreateView(generics.CreateAPIView):
    serializer_class = InterviewAnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(session_id=self.kwargs["session_id"])


# ── Mentorship ────────────────────────────────────────────────────────────────

class MentorListView(generics.ListAPIView):
    serializer_class = MentorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = MentorProfile.objects.filter(is_available=True).select_related("district")
        industry = self.request.query_params.get("industry")
        search = self.request.query_params.get("search")
        free_only = self.request.query_params.get("free")
        if industry:
            qs = qs.filter(industry__icontains=industry)
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(
                skills__contains=[search]
            )
        if free_only == "true":
            qs = qs.filter(hourly_rate_lkr=0)
        return qs


class MentorDetailView(generics.RetrieveAPIView):
    serializer_class = MentorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = MentorProfile.objects.select_related("district")


class MentorshipRequestCreateView(generics.CreateAPIView):
    serializer_class = MentorshipRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


class MentorshipRequestListView(generics.ListAPIView):
    serializer_class = MentorshipRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MentorshipRequest.objects.filter(
            seeker=self.request.user
        ).select_related("mentor")


# ── Networking Drafts ─────────────────────────────────────────────────────────

class NetworkingDraftListCreateView(generics.ListCreateAPIView):
    serializer_class = NetworkingDraftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NetworkingDraft.objects.filter(user=self.request.user)


class NetworkingDraftDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NetworkingDraftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NetworkingDraft.objects.filter(user=self.request.user)


# ── Brand Score ───────────────────────────────────────────────────────────────

class BrandScoreView(generics.ListCreateAPIView):
    serializer_class = BrandScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BrandScore.objects.filter(user=self.request.user)[:1]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ── Career Roadmap ────────────────────────────────────────────────────────────

class CareerRoadmapListCreateView(generics.ListCreateAPIView):
    serializer_class = CareerRoadmapSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CareerRoadmap.objects.filter(user=self.request.user)


class CareerRoadmapDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CareerRoadmapSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CareerRoadmap.objects.filter(user=self.request.user)
