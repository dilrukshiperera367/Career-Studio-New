"""Portal API views — public/anonymous candidate-facing endpoints."""

from rest_framework import serializers, viewsets, status
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.utils import timezone


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class PortalApplySerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, default="")
    job_id = serializers.UUIDField()
    consent_data_processing = serializers.BooleanField(default=False)


# ---------------------------------------------------------------------------
# Core portal views (public application flow)
# ---------------------------------------------------------------------------

class PortalApplyView(APIView):
    """Public endpoint: anonymous candidate application."""
    permission_classes = [AllowAny]

    def post(self, request):
        ser = PortalApplySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Get the job and its tenant
        from apps.jobs.models import Job
        try:
            job = Job.objects.get(id=data["job_id"], status="open")
        except Job.DoesNotExist:
            return Response({"error": "Job not found or closed"}, status=status.HTTP_404_NOT_FOUND)

        tenant_id = str(job.tenant_id)

        # Resolve/create candidate
        from apps.candidates.services import resolve_candidate
        from apps.candidates.models import Candidate, CandidateIdentity

        result = resolve_candidate(
            tenant_id=tenant_id,
            full_name=data["full_name"],
            email=data["email"],
            phone=data.get("phone"),
        )

        if result["action"] in ("existing", "auto_linked"):
            candidate_id = result["candidate_id"]
        else:
            candidate = Candidate.objects.create(
                tenant_id=tenant_id,
                full_name=data["full_name"],
                primary_email=data["email"],
                primary_phone=data.get("phone", ""),
                source="portal",
            )
            candidate_id = candidate.id

            # Create identity records
            CandidateIdentity.objects.create(
                tenant_id=tenant_id,
                candidate=candidate,
                identity_type="email",
                identity_value=data["email"].lower().strip(),
            )

        # Create application
        from apps.applications.models import Application, StageHistory
        from apps.jobs.models import PipelineStage

        # Check if already applied
        if Application.objects.filter(
            job_id=data["job_id"],
            candidate_id=candidate_id,
            tenant_id=tenant_id,
        ).exists():
            return Response({"error": "Already applied"}, status=status.HTTP_409_CONFLICT)

        first_stage = PipelineStage.objects.filter(
            job=job, tenant_id=tenant_id,
        ).order_by("order").first()

        app = Application.objects.create(
            tenant_id=tenant_id,
            job=job,
            candidate_id=candidate_id,
            current_stage=first_stage,
            source="portal",
        )

        StageHistory.objects.create(
            tenant_id=tenant_id,
            application=app,
            to_stage=first_stage,
            notes="Applied via portal",
        )

        # Record consent
        if data.get("consent_data_processing"):
            from apps.consent.models import ConsentRecord
            ConsentRecord.objects.create(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                consent_type="data_processing",
                granted=True,
                granted_at=timezone.now(),
                ip_address=request.META.get("REMOTE_ADDR"),
            )

        # Generate status tracking token
        import jwt
        from django.conf import settings
        from datetime import datetime, timedelta

        token_payload = {
            "application_id": str(app.id),
            "candidate_id": str(candidate_id),
            "tenant_id": tenant_id,
            "exp": datetime.utcnow() + timedelta(days=90),
        }
        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        tracking_token = jwt.encode(token_payload, portal_secret, algorithm="HS256")

        return Response({
            "application_id": str(app.id),
            "tracking_token": tracking_token,
            "status": "applied",
            "message": "Application submitted successfully",
        }, status=status.HTTP_201_CREATED)


class PortalStatusView(APIView):
    """Public endpoint: check application status via signed token."""
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response({"error": "token required"}, status=status.HTTP_400_BAD_REQUEST)

        import jwt
        from django.conf import settings

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        from apps.applications.models import Application

        try:
            app = Application.objects.select_related("current_stage", "job").get(
                id=payload["application_id"],
                tenant_id=payload["tenant_id"],
            )
        except Application.DoesNotExist:
            return Response({"error": "Application not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "application_id": str(app.id),
            "job_title": app.job.title,
            "current_stage": app.current_stage.name if app.current_stage else None,
            "status": app.status,
            "applied_at": app.created_at.isoformat(),
        })


class PortalJobAlertView(APIView):
    """Public: subscribe to job alerts."""
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.portal.models import JobAlert
        from apps.tenants.models import Tenant

        tenant_slug = request.data.get("tenant_slug", "")
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Response({"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND)

        alert, created = JobAlert.objects.get_or_create(
            tenant=tenant,
            email=request.data.get("email", ""),
            defaults={
                "name": request.data.get("name", ""),
                "keywords": request.data.get("keywords", []),
                "department": request.data.get("department", ""),
                "location": request.data.get("location", ""),
            },
        )

        return Response({
            "id": str(alert.id),
            "email": alert.email,
            "created": created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PortalFeedbackView(APIView):
    """Public: post-rejection feedback from candidate."""
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.portal.models import PortalToken, CandidateFeedback

        token = request.data.get("token")
        if not token:
            return Response({"error": "token required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            portal_token = PortalToken.objects.get(
                token=token, purpose="feedback"
            )
        except PortalToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

        if portal_token.expires_at < timezone.now():
            return Response({"error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)

        feedback = CandidateFeedback.objects.create(
            tenant=portal_token.tenant,
            candidate=portal_token.candidate,
            application=portal_token.application,
            overall_rating=request.data.get("rating", 3),
            comments=request.data.get("comments", ""),
            would_apply_again=request.data.get("would_apply_again"),
        )

        portal_token.used_at = timezone.now()
        portal_token.save(update_fields=["used_at"])

        return Response({"id": str(feedback.id), "message": "Thank you for your feedback"}, status=status.HTTP_201_CREATED)


class PortalCareerPageView(APIView):
    """Public: career page configuration and job listings."""
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.tenants.models import Tenant, TenantSettings
        from apps.jobs.models import Job

        tenant_slug = request.query_params.get("tenant")
        if not tenant_slug:
            return Response({"error": "tenant parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Response({"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get career page config
        try:
            settings_obj = TenantSettings.objects.get(tenant=tenant)
            career_config = settings_obj.career_page_config or {}
        except TenantSettings.DoesNotExist:
            career_config = {}

        # Get open public jobs
        jobs = Job.objects.filter(
            tenant=tenant, status="open", internal_only=False,
        ).values(
            "id", "title", "department", "location", "is_remote",
            "employment_type", "salary_min", "salary_max", "salary_currency",
            "published_at", "application_deadline",
        ).order_by("-published_at")[:50]

        return Response({
            "company": {
                "name": tenant.name,
                "slug": tenant.slug,
                "config": career_config,
            },
            "jobs": list(jobs),
        })


# ---------------------------------------------------------------------------
# Portal self-service endpoints (Features 114-117, 121)
# ---------------------------------------------------------------------------

class PortalDocumentUploadView(APIView):
    """Candidate uploads additional documents via secure link."""
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt
        from django.conf import settings

        token = request.data.get("token")
        if not token:
            return Response({"error": "Token required"}, status=400)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "document_upload":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        # Save uploaded file
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided"}, status=400)

        from apps.candidates.models import ResumeDocument, Candidate

        try:
            candidate = Candidate.objects.get(
                id=payload["candidate_id"], tenant_id=payload["tenant_id"]
            )
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found"}, status=404)

        # Save file
        from django.core.files.storage import default_storage
        path = default_storage.save(
            f"candidates/{candidate.id}/documents/{file.name}", file
        )

        # Create as new resume version
        latest = ResumeDocument.objects.filter(candidate=candidate).order_by("-version").first()
        version = (latest.version + 1) if latest else 1

        doc = ResumeDocument.objects.create(
            tenant_id=payload["tenant_id"],
            candidate=candidate,
            version=version,
            file_url=path,
            file_type=file.content_type or "application/octet-stream",
        )

        return Response({
            "document_id": str(doc.id),
            "version": version,
            "file_url": path,
            "status": "uploaded",
        }, status=201)


class PortalProfileUpdateView(APIView):
    """Candidate updates their contact info/skills through portal."""
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt
        from django.conf import settings

        token = request.data.get("token")
        if not token:
            return Response({"error": "Token required"}, status=400)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "profile_update":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        from apps.candidates.models import Candidate

        try:
            candidate = Candidate.objects.get(
                id=payload["candidate_id"], tenant_id=payload["tenant_id"]
            )
        except Candidate.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        # Update allowed fields
        allowed = ["primary_phone", "location", "headline", "linkedin_url",
                    "github_url", "portfolio_url", "availability", "preferred_contact"]
        updated_fields = []
        for field in allowed:
            if field in request.data:
                setattr(candidate, field, request.data[field])
                updated_fields.append(field)

        if updated_fields:
            updated_fields.append("updated_at")
            candidate.save(update_fields=updated_fields)

        return Response({"updated_fields": updated_fields, "status": "updated"})


class PortalSelfScheduleView(APIView):
    """Candidate self-schedules interview from available time slots."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Get available time slots."""
        import jwt
        from django.conf import settings

        token = request.query_params.get("token")
        if not token:
            return Response({"error": "Token required"}, status=400)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "self_schedule":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        from apps.applications.models import Interview

        # Return pending interviews that need scheduling
        interviews = Interview.objects.filter(
            application_id=payload.get("application_id"),
            tenant_id=payload["tenant_id"],
            status="pending",
        ).values("id", "interview_type", "round_name", "round_number")

        return Response({"interviews": list(interviews)})

    def post(self, request):
        """Candidate selects a time slot."""
        import jwt
        from django.conf import settings
        from datetime import date, time

        token = request.data.get("token")
        if not token:
            return Response({"error": "Token required"}, status=400)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "self_schedule":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        from apps.applications.models import Interview

        interview_id = request.data.get("interview_id")
        selected_date = request.data.get("date")
        selected_time = request.data.get("time")

        if not all([interview_id, selected_date, selected_time]):
            return Response({"error": "interview_id, date, and time required"}, status=400)

        try:
            interview = Interview.objects.get(
                id=interview_id,
                tenant_id=payload["tenant_id"],
                status="pending",
            )
            interview.date = date.fromisoformat(selected_date)
            interview.time = time.fromisoformat(selected_time)
            interview.status = "scheduled"
            interview.save(update_fields=["date", "time", "status", "updated_at"])

            return Response({
                "interview_id": str(interview.id),
                "date": str(interview.date),
                "time": str(interview.time),
                "status": "scheduled",
            })
        except Interview.DoesNotExist:
            return Response({"error": "Interview not found"}, status=404)


# Views extracted to dedicated modules — re-imported here so portal_urlpatterns can reference them
from .offers import PortalOfferReviewView  # noqa: E402
from .referrals import PortalReferralView  # noqa: E402


class PortalApplicationStatusView(APIView):
    """
    GET /api/v1/portal/application-status/?token=<jwt>
    Returns detailed application status including stage history.
    Token must be a signed JWT containing application_id, candidate_id, tenant_id.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        import jwt
        from django.conf import settings

        token = request.query_params.get("token")
        if not token:
            return Response({"error": "token required"}, status=status.HTTP_400_BAD_REQUEST)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        from apps.applications.models import Application, StageHistory

        try:
            app = Application.objects.select_related(
                "current_stage", "job", "candidate"
            ).get(
                id=payload["application_id"],
                tenant_id=payload["tenant_id"],
            )
        except Application.DoesNotExist:
            return Response({"error": "Application not found"}, status=status.HTTP_404_NOT_FOUND)

        history = StageHistory.objects.filter(
            application=app
        ).select_related("from_stage", "to_stage").order_by("created_at")

        stage_history = [
            {
                "from_stage": h.from_stage.name if h.from_stage else None,
                "to_stage": h.to_stage.name if h.to_stage else None,
                "notes": h.notes or "",
                "moved_at": h.created_at.isoformat(),
            }
            for h in history
        ]

        return Response({
            "application_id": str(app.id),
            "job_title": app.job.title,
            "candidate_name": app.candidate.full_name if app.candidate else "",
            "current_stage": app.current_stage.name if app.current_stage else None,
            "status": app.status,
            "is_priority": app.is_priority,
            "applied_at": app.created_at.isoformat(),
            "updated_at": app.updated_at.isoformat(),
            "stage_history": stage_history,
        })


# ---------------------------------------------------------------------------
# Admin-facing ViewSets — CandidateNPS and SavedApplicationDraft
# ---------------------------------------------------------------------------

class CandidateNPSSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.portal.models import CandidateNPS
        model = CandidateNPS
        fields = [
            "id", "candidate", "application", "event",
            "score", "comment", "responded_at",
        ]
        read_only_fields = ["id", "responded_at"]


class CandidateNPSViewSet(viewsets.ModelViewSet):
    """Admin: view and manage candidate NPS responses."""
    permission_classes = [IsAuthenticated]
    serializer_class = CandidateNPSSerializer

    def get_queryset(self):
        from apps.portal.models import CandidateNPS
        return CandidateNPS.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("candidate", "application").order_by("-responded_at")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class SavedApplicationDraftSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.portal.models import SavedApplicationDraft
        model = SavedApplicationDraft
        fields = [
            "id", "candidate", "job", "session_key",
            "draft_data", "resume_file_url", "last_saved_at", "created_at",
        ]
        read_only_fields = ["id", "last_saved_at", "created_at"]


class SavedApplicationDraftViewSet(viewsets.ModelViewSet):
    """Admin: view and manage saved application drafts."""
    permission_classes = [IsAuthenticated]
    serializer_class = SavedApplicationDraftSerializer

    def get_queryset(self):
        from apps.portal.models import SavedApplicationDraft
        return SavedApplicationDraft.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("candidate", "job").order_by("-last_saved_at")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


_admin_router = DefaultRouter()
_admin_router.register("nps", CandidateNPSViewSet, basename="portal-nps")
_admin_router.register("drafts", SavedApplicationDraftViewSet, basename="portal-drafts")


# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------

portal_urlpatterns = [
    path("apply/", PortalApplyView.as_view(), name="portal-apply"),
    path("status/", PortalStatusView.as_view(), name="portal-status"),
    path("application-status/", PortalApplicationStatusView.as_view(), name="portal-application-status"),
    path("job-alerts/", PortalJobAlertView.as_view(), name="portal-job-alerts"),
    path("feedback/", PortalFeedbackView.as_view(), name="portal-feedback"),
    path("career-page/", PortalCareerPageView.as_view(), name="portal-career-page"),
    # NEW — Portal self-service
    path("upload/", PortalDocumentUploadView.as_view(), name="portal-upload"),
    path("profile/", PortalProfileUpdateView.as_view(), name="portal-profile"),
    path("self-schedule/", PortalSelfScheduleView.as_view(), name="portal-self-schedule"),
    path("offer-review/", PortalOfferReviewView.as_view(), name="portal-offer-review"),
    path("referral/", PortalReferralView.as_view(), name="portal-referral"),
    # Admin-facing NPS and draft management
    path("admin/", include(_admin_router.urls)),
]
