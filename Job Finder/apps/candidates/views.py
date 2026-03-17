"""Candidates views - seeker profile, resumes, and related profile sections."""
from django.utils import timezone
from rest_framework import generics, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsSeeker
from .models import (
    SeekerProfile,
    SeekerResume,
    SeekerSkill,
    SeekerExperience,
    SeekerEducation,
    SeekerCertification,
    SeekerLanguage,
    SeekerReference,
    SeekerPortfolio,
    SkillEndorsement,
)
from .serializers import (
    SeekerProfileSerializer,
    SeekerProfileUpdateSerializer,
    SeekerResumeSerializer,
    SeekerSkillSerializer,
    SeekerExperienceSerializer,
    SeekerEducationSerializer,
    SeekerCertificationSerializer,
    SeekerLanguageSerializer,
    SeekerReferenceSerializer,
    SeekerPortfolioSerializer,
    ProfileCompletenessSerializer,
    WizardStepSerializer,
)


def get_or_create_profile(user):
    return SeekerProfile.objects.get_or_create(user=user)[0]


class SeekerProfileView(generics.RetrieveUpdateAPIView):
    """Current user's seeker profile."""

    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_object(self):
        return get_or_create_profile(self.request.user)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return SeekerProfileUpdateSerializer
        return SeekerProfileSerializer

    def perform_update(self, serializer):
        profile = serializer.save(last_profile_edit=timezone.now())
        profile.compute_completeness()
        profile.save(update_fields=["profile_completeness", "updated_at"])


class SeekerProfilePublicView(generics.RetrieveAPIView):
    """Public-facing seeker profile (visibility controlled)."""

    serializer_class = SeekerProfileSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"

    def get_queryset(self):
        return SeekerProfile.objects.filter(profile_visibility="public")


class SeekerProfilePreviewView(generics.RetrieveAPIView):
    """Authenticated preview with seeker-only data."""

    serializer_class = SeekerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_object(self):
        return get_or_create_profile(self.request.user)


class ProfileCompletenessView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        score = profile.compute_completeness()
        profile.save(update_fields=["profile_completeness", "updated_at"])
        payload = {
            "profile_completeness": score,
            "profile_strength": "red" if score < 40 else "yellow" if score <= 70 else "green",
            "suggestions": profile.get_suggestions(),
        }
        return Response(ProfileCompletenessSerializer(payload).data)


class WizardStepUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request):
        profile = get_or_create_profile(request.user)
        serializer = WizardStepSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile.wizard_step = serializer.validated_data["wizard_step"]
        if "wizard_completed" in serializer.validated_data:
            profile.wizard_completed = serializer.validated_data["wizard_completed"]
        profile.save(update_fields=["wizard_step", "wizard_completed", "updated_at"])
        return Response({"wizard_step": profile.wizard_step, "wizard_completed": profile.wizard_completed})


class ResumeListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerResumeSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        return SeekerResume.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class ResumeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerResumeSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        return SeekerResume.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_update(self, serializer):
        serializer.save()
        profile = get_or_create_profile(self.request.user)
        profile.compute_completeness()
        profile.save(update_fields=["profile_completeness", "updated_at"])

    def perform_destroy(self, instance):
        was_primary = instance.is_primary
        seeker = instance.seeker
        instance.delete()
        if was_primary:
            next_resume = seeker.resumes.order_by("-uploaded_at").first()
            if next_resume:
                next_resume.is_primary = True
                next_resume.save(update_fields=["is_primary"])


class ResumeSetPrimaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        seeker = get_or_create_profile(request.user)
        try:
            resume = seeker.resumes.get(pk=pk)
        except SeekerResume.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        seeker.resumes.exclude(pk=resume.pk).update(is_primary=False)
        resume.is_primary = True
        resume.save(update_fields=["is_primary"])
        return Response({"detail": "Primary resume updated."})


class ResumeRefreshView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        seeker = get_or_create_profile(request.user)
        try:
            resume = seeker.resumes.get(pk=pk)
        except SeekerResume.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        resume.refreshed_at = timezone.now()
        resume.save(update_fields=["refreshed_at"])
        return Response({"detail": "Resume refreshed.", "refreshed_at": resume.refreshed_at})


class ResumeRetryParseView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        seeker = get_or_create_profile(request.user)
        try:
            resume = seeker.resumes.get(pk=pk)
        except SeekerResume.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        resume.parse_status = "pending"
        resume.save(update_fields=["parse_status"])
        return Response({"detail": "Resume parsing queued.", "parse_status": "pending"})


class SkillListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerSkillSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerSkill.objects.filter(seeker=get_or_create_profile(self.request.user)).select_related("skill")

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerSkillSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerSkill.objects.filter(seeker=get_or_create_profile(self.request.user))


class ExperienceListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerExperienceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerExperience.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class ExperienceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerExperienceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerExperience.objects.filter(seeker=get_or_create_profile(self.request.user))


class EducationListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerEducationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerEducation.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class EducationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerEducationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerEducation.objects.filter(seeker=get_or_create_profile(self.request.user))


class CertificationListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerCertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerCertification.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class CertificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerCertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerCertification.objects.filter(seeker=get_or_create_profile(self.request.user))


class LanguageListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerLanguageSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerLanguage.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class LanguageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerLanguageSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerLanguage.objects.filter(seeker=get_or_create_profile(self.request.user))


class ReferenceListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerReferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerReference.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class ReferenceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerReferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return SeekerReference.objects.filter(seeker=get_or_create_profile(self.request.user))


class PortfolioListCreateView(generics.ListCreateAPIView):
    serializer_class = SeekerPortfolioSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return SeekerPortfolio.objects.filter(seeker=get_or_create_profile(self.request.user))

    def perform_create(self, serializer):
        serializer.save(seeker=get_or_create_profile(self.request.user))


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SeekerPortfolioSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return SeekerPortfolio.objects.filter(seeker=get_or_create_profile(self.request.user))
