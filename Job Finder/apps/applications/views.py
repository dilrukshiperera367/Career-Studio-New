"""Applications views — Apply, track, manage (seeker + employer sides)."""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsSeeker, IsEmployer
from apps.employers.models import EmployerTeamMember
from .models import Application, ApplicationStatusHistory, ApplicationNote, InterviewSchedule, JobOffer
from .serializers import (
    ApplicationCreateSerializer, ApplicationSerializer,
    ApplicationEmployerSerializer, ApplicationStatusUpdateSerializer,
    ApplicationStatusHistorySerializer, ApplicationNoteSerializer,
    InterviewScheduleSerializer, JobOfferSerializer, OfferRespondSerializer,
    ApplicationDraftSerializer,
)


# ── Seeker side ───────────────────────────────────────────────────────────

class ApplyView(generics.CreateAPIView):
    """Submit an application (seeker)."""
    serializer_class = ApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def perform_create(self, serializer):
        job = serializer.validated_data["job"]
        serializer.save(
            applicant=self.request.user,
            employer=job.employer,
        )
        job.application_count += 1
        job.save(update_fields=["application_count"])


class MyApplicationsView(generics.ListAPIView):
    """List seeker's own applications."""
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return Application.objects.filter(
            applicant=self.request.user,
        ).select_related("job__employer").order_by("-submitted_at")


class MyApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return Application.objects.filter(applicant=self.request.user)


class WithdrawApplicationView(APIView):
    """Withdraw an application (seeker)."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        try:
            app = Application.objects.get(pk=pk, applicant=request.user)
        except Application.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if app.status in ("withdrawn", "hired", "rejected"):
            return Response({"detail": "Cannot withdraw at this stage."}, status=status.HTTP_400_BAD_REQUEST)
        old_status = app.status
        app.status = "withdrawn"
        app.withdrawn_at = timezone.now()
        app.save(update_fields=["status", "withdrawn_at", "updated_at"])
        ApplicationStatusHistory.objects.create(
            application=app, old_status=old_status, new_status="withdrawn",
            changed_by=request.user, notes="Withdrawn by applicant.",
        )
        return Response({"detail": "Application withdrawn."})


# ── Employer side ─────────────────────────────────────────────────────────

class EmployerApplicationsView(generics.ListAPIView):
    """List applications received for employer's jobs."""
    serializer_class = ApplicationEmployerSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if not membership:
            return Application.objects.none()
        qs = Application.objects.filter(employer=membership.employer).select_related("applicant", "job")
        job_id = self.request.query_params.get("job")
        if job_id:
            qs = qs.filter(job_id=job_id)
        stat = self.request.query_params.get("status")
        if stat:
            qs = qs.filter(status=stat)
        return qs.order_by("-submitted_at")


class EmployerApplicationDetailView(generics.RetrieveUpdateAPIView):
    """Employer view/update a single application."""
    serializer_class = ApplicationEmployerSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if not membership:
            return Application.objects.none()
        return Application.objects.filter(employer=membership.employer)


class UpdateApplicationStatusView(APIView):
    """Employer updates application status."""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request, pk):
        membership = EmployerTeamMember.objects.filter(user=request.user).first()
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            app = Application.objects.get(pk=pk, employer=membership.employer)
        except Application.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = app.status
        new_status = serializer.validated_data["status"]
        app.status = new_status

        # Update relevant timestamps
        ts_map = {
            "viewed": "viewed_at", "shortlisted": "shortlisted_at",
            "interview": "interviewed_at", "offer": "offered_at",
            "hired": "hired_at", "rejected": "rejected_at",
        }
        if field := ts_map.get(new_status):
            setattr(app, field, timezone.now())
        app.save()

        ApplicationStatusHistory.objects.create(
            application=app, old_status=old_status, new_status=new_status,
            changed_by=request.user, notes=serializer.validated_data.get("notes", ""),
        )
        return Response({"detail": f"Status updated to {new_status}."})


class ApplicationStatusHistoryView(generics.ListAPIView):
    serializer_class = ApplicationStatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ApplicationStatusHistory.objects.filter(application_id=self.kwargs["pk"])


# ── Draft saving (#281) ───────────────────────────────────────────────────

class SaveDraftApplicationView(APIView):
    """Save or update an application draft before final submission."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request):
        # Check if draft already exists for this job
        job_id = request.data.get("job")
        existing = Application.objects.filter(applicant=request.user, job_id=job_id, status="draft").first()
        if existing:
            serializer = ApplicationDraftSerializer(existing, data=request.data, partial=True, context={"request": request})
        else:
            serializer = ApplicationDraftSerializer(data=request.data, context={"request": request})

        serializer.is_valid(raise_exception=True)
        app = serializer.save(applicant=request.user, employer=serializer.validated_data["job"].employer, status="draft")
        return Response(ApplicationSerializer(app).data, status=status.HTTP_200_OK)


class SubmitDraftView(APIView):
    """Promote a draft application to submitted."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        try:
            app = Application.objects.get(pk=pk, applicant=request.user, status="draft")
        except Application.DoesNotExist:
            return Response({"detail": "Draft not found."}, status=status.HTTP_404_NOT_FOUND)
        app.status = "submitted"
        app.save(update_fields=["status", "updated_at"])
        app.job.application_count = Application.objects.filter(job=app.job, status__in=["submitted", "viewed", "shortlisted"]).count()
        app.job.save(update_fields=["application_count"])
        return Response(ApplicationSerializer(app).data)


# ── Seeker notes (#283) ───────────────────────────────────────────────────

class ApplicationNoteListCreateView(generics.ListCreateAPIView):
    serializer_class = ApplicationNoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return ApplicationNote.objects.filter(
            application_id=self.kwargs["pk"],
            application__applicant=self.request.user,
        )

    def perform_create(self, serializer):
        serializer.save(application_id=self.kwargs["pk"])


class ApplicationNoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ApplicationNoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return ApplicationNote.objects.filter(
            application__applicant=self.request.user,
        )


# ── Interview scheduling (#291) ───────────────────────────────────────────

class InterviewListCreateView(generics.ListCreateAPIView):
    serializer_class = InterviewScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_application(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if not membership:
            return None
        return Application.objects.filter(pk=self.kwargs["pk"], employer=membership.employer).first()

    def get_queryset(self):
        app = self.get_application()
        return InterviewSchedule.objects.filter(application=app) if app else InterviewSchedule.objects.none()

    def perform_create(self, serializer):
        app = self.get_application()
        serializer.save(application=app)


class InterviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InterviewScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if not membership:
            return InterviewSchedule.objects.none()
        return InterviewSchedule.objects.filter(application__employer=membership.employer)


class SeekerInterviewListView(generics.ListAPIView):
    """Seeker's own interview schedule across all applications."""
    serializer_class = InterviewScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return InterviewSchedule.objects.filter(
            application__applicant=self.request.user,
        ).select_related("application__job").order_by("scheduled_at")


class ConfirmInterviewView(APIView):
    """Seeker confirms interview attendance."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        try:
            interview = InterviewSchedule.objects.get(
                pk=pk, application__applicant=request.user,
            )
        except InterviewSchedule.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        interview.is_confirmed = True
        interview.save(update_fields=["is_confirmed"])
        return Response({"confirmed": True})


# ── Offer management (#292) ───────────────────────────────────────────────

class CreateOfferView(generics.CreateAPIView):
    """Employer creates a job offer for a hired application."""
    serializer_class = JobOfferSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def perform_create(self, serializer):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        app = Application.objects.get(pk=self.kwargs["pk"], employer=membership.employer)
        serializer.save(application=app)


class OfferDetailView(generics.RetrieveAPIView):
    """Retrieve offer details (seeker or employer)."""
    serializer_class = JobOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        pk = self.kwargs["pk"]
        try:
            offer = JobOffer.objects.get(
                application__pk=pk,
            )
            # Allow access if seeker or employer team member
            if offer.application.applicant == user:
                return offer
            membership = EmployerTeamMember.objects.filter(user=user).first()
            if membership and offer.application.employer == membership.employer:
                return offer
        except JobOffer.DoesNotExist:
            pass
        from django.http import Http404
        raise Http404


class RespondToOfferView(APIView):
    """Seeker accepts or declines a job offer."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        try:
            offer = JobOffer.objects.get(application__pk=pk, application__applicant=request.user)
        except JobOffer.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = OfferRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "accept":
            offer.offer_status = "accepted"
            offer.application.status = "hired"
            offer.application.hired_at = timezone.now()
            offer.application.save(update_fields=["status", "hired_at", "updated_at"])
        elif action == "decline":
            offer.offer_status = "declined"
            offer.declined_reason = serializer.validated_data.get("declined_reason", "")
        elif action == "negotiate":
            offer.offer_status = "negotiating"

        offer.responded_at = timezone.now()
        offer.save()
        return Response(JobOfferSerializer(offer).data)
