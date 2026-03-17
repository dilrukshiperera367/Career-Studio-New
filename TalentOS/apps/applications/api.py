"""API for Applications app — CRUD + stage transitions + evaluations."""

import uuid
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.applications.models import (
    Application, StageHistory, Evaluation, Interview, Offer,
    InterviewPanel, InterviewScorecard, Employee, OnboardingTask,
    DebriefSession, CalibrationSession, ApplicationAppeal, HiringManagerNote,
)
from apps.jobs.models import PipelineStage
from apps.accounts.permissions import IsRecruiter, IsInterviewer, HasTenantAccess


# ── Serializers ──────────────────────────────────────────────────────────────

class StageHistorySerializer(serializers.ModelSerializer):
    from_stage_name = serializers.CharField(source="from_stage.name", read_only=True, default=None)
    to_stage_name = serializers.CharField(source="to_stage.name", read_only=True)

    class Meta:
        model = StageHistory
        fields = ["id", "from_stage", "from_stage_name", "to_stage", "to_stage_name", "actor", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


class EvaluationSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.CharField(source="evaluator.get_full_name", read_only=True, default="")

    class Meta:
        model = Evaluation
        fields = [
            "id", "stage", "evaluator", "evaluator_name",
            "overall_rating", "recommendation", "criteria_scores",
            "strengths", "concerns", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ApplicationSerializer(serializers.ModelSerializer):
    stage_history = StageHistorySerializer(many=True, read_only=True)
    evaluations = EvaluationSerializer(many=True, read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "job", "job_title", "candidate", "candidate_name",
            "resume", "current_stage", "current_stage_name", "status",
            "source", "screening_answers", "score", "score_breakdown",
            "tags", "notes",
            "rejection_reason", "rejection_notes", "is_priority",
            "on_hold", "hold_reason", "stage_checklist_completed",
            "assigned_recruiter",
            "stage_history", "evaluations",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "score", "score_breakdown",
            "created_at", "updated_at",
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["job", "candidate", "resume", "source", "screening_answers"]


# ── ViewSets ─────────────────────────────────────────────────────────────────

class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job", "status", "source", "is_priority", "on_hold", "current_stage"]
    search_fields = ["candidate__full_name", "job__title"]
    ordering_fields = ["created_at", "updated_at", "score", "is_priority"]

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        return ApplicationSerializer

    def get_queryset(self):
        return Application.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related(
            "job", "candidate", "current_stage"
        ).prefetch_related("stage_history", "evaluations")

    def perform_create(self, serializer):
        job = serializer.validated_data["job"]
        # Get first stage (Applied)
        first_stage = PipelineStage.objects.filter(
            job=job, tenant_id=self.request.tenant_id,
        ).order_by("order").first()

        if not first_stage:
            raise serializers.ValidationError("Job has no pipeline stages")

        app = serializer.save(
            tenant_id=self.request.tenant_id,
            current_stage=first_stage,
        )

        # Initial stage history
        StageHistory.objects.create(
            tenant_id=self.request.tenant_id,
            application=app,
            from_stage=None,
            to_stage=first_stage,
            actor=self.request.user,
            notes="Application created",
        )

        # Trigger workflow event
        from apps.workflows.services import process_event
        process_event({
            "tenant_id": str(self.request.tenant_id),
            "event_type": "application_created",
            "event_id": str(app.id),
            "payload": {
                "application_id": str(app.id),
                "candidate_id": str(app.candidate_id),
                "job_id": str(app.job_id),
            },
        })

    @action(detail=True, methods=["post"])
    def move_stage(self, request, pk=None):
        """Move application to a new stage."""
        app = self.get_object()
        to_stage_id = request.data.get("to_stage_id")
        notes = request.data.get("notes", "")

        if not to_stage_id:
            return Response({"error": "to_stage_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            to_stage = PipelineStage.objects.get(
                id=to_stage_id, tenant_id=request.tenant_id,
            )
        except PipelineStage.DoesNotExist:
            return Response({"error": "Invalid stage"}, status=status.HTTP_404_NOT_FOUND)

        if str(to_stage.job_id) != str(app.job_id):
            return Response(
                {"error": "Target stage does not belong to this application's job"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from_stage = app.current_stage

        # Create immutable history record
        StageHistory.objects.create(
            tenant_id=request.tenant_id,
            application=app,
            from_stage=from_stage,
            to_stage=to_stage,
            actor=request.user,
            notes=notes,
        )

        # Update current stage
        app.current_stage = to_stage
        if to_stage.stage_type == "rejected":
            app.status = "rejected"
        elif to_stage.stage_type == "hired":
            app.status = "hired"
        app.save(update_fields=["current_stage", "status", "updated_at"])

        # Trigger workflow
        from apps.workflows.services import process_event
        process_event({
            "tenant_id": str(request.tenant_id),
            "event_type": "stage_changed",
            "event_id": str(uuid.uuid4()),
            "payload": {
                "application_id": str(app.id),
                "candidate_id": str(app.candidate_id),
                "job_id": str(app.job_id),
                "from_stage_type": from_stage.stage_type if from_stage else None,
                "to_stage_type": to_stage.stage_type,
            },
        })

        return Response(ApplicationSerializer(app).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject application."""
        app = self.get_object()
        notes = request.data.get("notes", "")

        reject_stage = PipelineStage.objects.filter(
            job=app.job, stage_type="rejected", tenant_id=request.tenant_id,
        ).first()

        if reject_stage:
            StageHistory.objects.create(
                tenant_id=request.tenant_id,
                application=app,
                from_stage=app.current_stage,
                to_stage=reject_stage,
                actor=request.user,
                notes=notes,
            )
            app.current_stage = reject_stage

        app.status = "rejected"
        app.rejection_reason = request.data.get("rejection_reason", "other")
        app.rejection_notes = notes
        app.save(update_fields=["current_stage", "status", "rejection_reason", "rejection_notes", "updated_at"])
        return Response(ApplicationSerializer(app).data)

    @action(detail=False, methods=["post"])
    def bulk_move_stage(self, request):
        """Move multiple applications to a stage."""
        app_ids = request.data.get("application_ids", [])
        stage_id = request.data.get("stage_id")
        if not app_ids or not stage_id:
            return Response({"error": "application_ids and stage_id required"}, status=status.HTTP_400_BAD_REQUEST)
        apps = Application.objects.filter(id__in=app_ids, tenant_id=request.tenant_id)
        stage = PipelineStage.objects.get(id=stage_id, tenant_id=request.tenant_id)
        moved = 0
        for app in apps:
            StageHistory.objects.create(
                tenant_id=request.tenant_id, application=app,
                from_stage=app.current_stage, to_stage=stage, actor=request.user,
            )
            app.current_stage = stage
            app.save(update_fields=["current_stage", "updated_at"])
            moved += 1
        return Response({"moved": moved})

    @action(detail=False, methods=["post"])
    def bulk_reject(self, request):
        """Reject multiple applications at once."""
        app_ids = request.data.get("application_ids", [])
        reason = request.data.get("rejection_reason", "other")
        apps = Application.objects.filter(id__in=app_ids, tenant_id=request.tenant_id, status="active")
        count = apps.update(status="rejected", rejection_reason=reason)
        return Response({"rejected": count})

    @action(detail=True, methods=["post"])
    def toggle_priority(self, request, pk=None):
        """Toggle star/pin on an application."""
        app = self.get_object()
        app.is_priority = not app.is_priority
        app.save(update_fields=["is_priority", "updated_at"])
        return Response({"is_priority": app.is_priority})

    @action(detail=True, methods=["post"])
    def toggle_hold(self, request, pk=None):
        """Put application on hold or remove from hold."""
        app = self.get_object()
        app.on_hold = not app.on_hold
        app.hold_reason = request.data.get("reason", "")
        if app.on_hold:
            app.status = "on_hold"
        else:
            app.status = "active"
        app.save(update_fields=["on_hold", "hold_reason", "status", "updated_at"])
        return Response(ApplicationSerializer(app).data)

    @action(detail=True, methods=["post"])
    def revive(self, request, pk=None):
        """Un-reject a candidate, move back to active stage."""
        app = self.get_object()
        if app.status != "rejected":
            return Response({"error": "Can only revive rejected applications"}, status=status.HTTP_400_BAD_REQUEST)
        first_stage = PipelineStage.objects.filter(
            job=app.job, tenant_id=request.tenant_id,
        ).order_by("order").first()
        if first_stage:
            app.current_stage = first_stage
        app.status = "active"
        app.rejection_reason = ""
        app.rejection_notes = ""
        app.save(update_fields=["current_stage", "status", "rejection_reason", "rejection_notes", "updated_at"])
        return Response(ApplicationSerializer(app).data)


class EvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = EvaluationSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsInterviewer]

    def get_queryset(self):
        return Evaluation.objects.filter(
            tenant_id=self.request.tenant_id,
            application_id=self.kwargs.get("application_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            evaluator=self.request.user,
            application_id=self.kwargs.get("application_pk"),
        )


# ── URLs ─────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("", ApplicationViewSet, basename="applications")

urlpatterns = [
    path("", include(router.urls)),
    path("<uuid:application_pk>/evaluations/", EvaluationViewSet.as_view({"get": "list", "post": "create"}), name="app-evaluations"),
    path("<uuid:application_pk>/evaluations/<uuid:pk>/", EvaluationViewSet.as_view({"get": "retrieve", "put": "update"}), name="app-evaluation-detail"),
]


# ══════════════════════════════════════════════════════════════════════════════
# INTERVIEW API (enhanced with panels, scorecards, rounds)
# ══════════════════════════════════════════════════════════════════════════════

class InterviewPanelSerializer(serializers.ModelSerializer):
    interviewer_name = serializers.CharField(source="interviewer.get_full_name", read_only=True, default="")

    class Meta:
        model = InterviewPanel
        fields = ["id", "interviewer", "interviewer_name", "status", "feedback", "rating", "submitted_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class InterviewScorecardSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewScorecard
        fields = ["id", "panel", "criteria_name", "rating", "notes"]
        read_only_fields = ["id"]


class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.CharField(source="candidate.primary_email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    panel_members = InterviewPanelSerializer(many=True, read_only=True)

    class Meta:
        model = Interview
        fields = [
            "id", "application", "candidate", "candidate_name", "candidate_email",
            "job", "job_title", "interview_type", "date", "time", "duration",
            "interviewer", "interviewer_name", "location", "status",
            "notes", "feedback", "rating",
            "round_number", "round_name", "no_show_by",
            "reschedule_count", "feedback_deadline", "decision",
            "panel_members",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InterviewViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["status", "interview_type", "candidate", "job", "interviewer"]
    search_fields = ["candidate__full_name", "job__title"]
    ordering_fields = ["date", "time", "created_at"]

    def get_queryset(self):
        return Interview.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("candidate", "job").prefetch_related("panel_members")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def add_panel_member(self, request, pk=None):
        """Add an interviewer to the panel."""
        interview = self.get_object()
        user_id = request.data.get("interviewer_id")
        if not user_id:
            return Response({"error": "interviewer_id required"}, status=status.HTTP_400_BAD_REQUEST)
        panel, created = InterviewPanel.objects.get_or_create(
            tenant_id=request.tenant_id, interview=interview,
            interviewer_id=user_id,
        )
        return Response(InterviewPanelSerializer(panel).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def submit_feedback(self, request, pk=None):
        """Panel member submits feedback + scorecard."""
        from django.utils import timezone
        interview = self.get_object()
        panel = InterviewPanel.objects.filter(
            interview=interview, interviewer=request.user
        ).first()
        if not panel:
            return Response({"error": "You are not on this panel"}, status=status.HTTP_403_FORBIDDEN)
        panel.feedback = request.data.get("feedback", "")
        panel.rating = request.data.get("rating")
        panel.status = "submitted"
        panel.submitted_at = timezone.now()
        panel.save()
        # Save scorecards
        for sc in request.data.get("scorecards", []):
            InterviewScorecard.objects.update_or_create(
                panel=panel, criteria_name=sc.get("criteria_name", ""),
                defaults={"rating": sc.get("rating", 3), "notes": sc.get("notes", "")},
            )
        return Response(InterviewPanelSerializer(panel).data)

    @action(detail=True, methods=["post"])
    def set_decision(self, request, pk=None):
        """Hiring manager sets post-interview decision."""
        interview = self.get_object()
        decision = request.data.get("decision", "")
        if decision not in ("advance", "reject", "hold"):
            return Response({"error": "decision must be advance, reject, or hold"}, status=status.HTTP_400_BAD_REQUEST)
        interview.decision = decision
        interview.save(update_fields=["decision", "updated_at"])
        return Response(InterviewSerializer(interview).data)

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        """Calendar view: all interviews for date range."""
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        qs = self.get_queryset()
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        return Response(InterviewSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def workload(self, request):
        """Interview load per interviewer this week."""
        from django.db.models import Count
        from django.utils import timezone
        import datetime
        today = timezone.now().date()
        week_start = today - datetime.timedelta(days=today.weekday())
        week_end = week_start + datetime.timedelta(days=6)
        data = Interview.objects.filter(
            tenant_id=request.tenant_id, date__gte=week_start, date__lte=week_end,
        ).values("interviewer__email", "interviewer__first_name", "interviewer__last_name"
        ).annotate(count=Count("id")).order_by("-count")
        return Response({"results": list(data)})


interview_router = DefaultRouter()
interview_router.register("", InterviewViewSet, basename="interviews")

interview_urlpatterns = [
    path("", include(interview_router.urls)),
]


# ══════════════════════════════════════════════════════════════════════════════
# OFFER API (enhanced with negotiation, decline reasons)
# ══════════════════════════════════════════════════════════════════════════════

class OfferSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id", "application", "candidate", "candidate_name",
            "job", "job_title", "salary", "salary_amount", "salary_currency",
            "start_date", "benefits", "equity", "signing_bonus", "bonus",
            "total_compensation", "status", "approval_status", "approver", "notes",
            "expires_at",
            "negotiation_history", "decline_reason", "decline_notes",
            "verbal_accepted", "background_check_status", "approval_chain",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OfferViewSet(viewsets.ModelViewSet):
    serializer_class = OfferSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "approval_status", "candidate", "job"]

    def get_queryset(self):
        return Offer.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("candidate", "job")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Mark offer as accepted — triggers Employee creation."""
        from django.utils import timezone
        offer = self.get_object()
        offer.status = "accepted"
        offer.save(update_fields=["status", "updated_at"])
        # Auto-create Employee record
        from apps.candidates.models import Candidate
        candidate = offer.candidate
        candidate.pool_status = "hired"
        candidate.save(update_fields=["pool_status", "updated_at"])
        # Create Employee
        employee, created = Employee.objects.get_or_create(
            tenant_id=request.tenant_id,
            candidate=candidate,
            defaults={
                "application": offer.application,
                "job": offer.job,
                "department": offer.job.department if offer.job else "",
                "title": offer.job.title if offer.job else "",
                "salary": offer.salary_amount,
                "salary_currency": offer.salary_currency,
                "hire_date": timezone.now().date(),
                "start_date": offer.start_date,
                "status": "onboarding",
            }
        )
        # Update job headcount
        if offer.job:
            offer.job.headcount_filled = (offer.job.headcount_filled or 0) + 1
            offer.job.save(update_fields=["headcount_filled"])

        # Dispatch Webhook to HRM System
        try:
            from apps.shared.tasks import send_webhook_task
            from django.conf import settings
            
            # Use environment variable or default HRM local URL
            hrm_webhook_url = getattr(settings, 'HRM_WEBHOOK_URL', 'http://127.0.0.1:8000/api/v1/integrations/ats/webhook/')
            hrm_webhook_secret = getattr(settings, 'HRM_WEBHOOK_SECRET', '')

            payload = {
                "event": "offer.accepted",
                "tenant_id": str(request.tenant_id),
                "data": {
                "candidate_id": str(candidate.id),
                    "full_name": candidate.full_name,
                    "email": candidate.primary_email,
                    "phone": candidate.primary_phone,
                    "start_date": str(offer.start_date) if offer.start_date else None,
                    "department_name": offer.job.department if offer.job else "",
                    "job_title": offer.job.title if offer.job else ""
                }
            }

            # Fire and forget via Celery or inline if celery is not running in sync
            send_webhook_task.delay(hrm_webhook_url, payload, hrm_webhook_secret)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to dispatch ATS webhook to HRM system: {e}")

        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Mark offer as declined with reason."""
        offer = self.get_object()
        offer.status = "declined"
        offer.decline_reason = request.data.get("reason", "other")
        offer.decline_notes = request.data.get("notes", "")
        offer.save(update_fields=["status", "decline_reason", "decline_notes", "updated_at"])
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def negotiate(self, request, pk=None):
        """Add a negotiation round."""
        offer = self.get_object()
        round_data = {
            "round": len(offer.negotiation_history) + 1,
            "offered": request.data.get("offered"),
            "counter": request.data.get("counter"),
            "notes": request.data.get("notes", ""),
            "date": str(timezone.now().date()) if hasattr(timezone, 'now') else "",
        }
        offer.negotiation_history.append(round_data)
        if request.data.get("new_salary"):
            offer.salary_amount = request.data["new_salary"]
        offer.save(update_fields=["negotiation_history", "salary_amount", "updated_at"])
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["get"], url_path="offer-pdf")
    def offer_pdf(self, request, pk=None):
        """GET /api/v1/offers/{id}/offer-pdf/ — download offer letter as PDF"""
        from apps.shared.pdf import offer_letter_pdf_response
        from datetime import date, timedelta
        instance = self.get_object()
        # Build salary display string
        if instance.salary_amount:
            salary_display = f"{instance.salary_currency} {instance.salary_amount:,.2f}"
        elif instance.salary:
            salary_display = instance.salary
        else:
            salary_display = "Competitive"
        # Build context from the Offer model instance
        context = {
            "company_name": getattr(request.tenant, "name", "ConnectOS") if hasattr(request, "tenant") else "ConnectOS",
            "candidate_name": instance.candidate.full_name if hasattr(instance.candidate, "full_name") else f"{instance.candidate.first_name} {instance.candidate.last_name}",
            "job_title": instance.job.title if instance.job else "Position",
            "department": instance.job.department if instance.job else "",
            "start_date": str(instance.start_date) if instance.start_date else "",
            "salary": salary_display,
            "employment_type": "Full-time",
            "location": instance.job.location if instance.job else "",
            "offer_date": date.today().strftime("%B %d, %Y"),
            "expiry_date": (date.today() + timedelta(days=7)).strftime("%B %d, %Y"),
        }
        return offer_letter_pdf_response(context)


offer_router = DefaultRouter()
offer_router.register("", OfferViewSet, basename="offers")

offer_urlpatterns = [
    path("", include(offer_router.urls)),
]


# ══════════════════════════════════════════════════════════════════════════════
# EMPLOYEE API
# ══════════════════════════════════════════════════════════════════════════════

class OnboardingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTask
        fields = ["id", "title", "description", "category", "due_date",
                  "assigned_to", "completed", "completed_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class EmployeeSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.CharField(source="candidate.primary_email", read_only=True)
    job_title_hired = serializers.CharField(source="job.title", read_only=True, default="")
    onboarding_tasks = OnboardingTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id", "candidate", "candidate_name", "candidate_email",
            "application", "job", "job_title_hired",
            "employee_id", "department", "title", "manager", "buddy",
            "hire_date", "start_date", "probation_end_date",
            "salary", "salary_currency", "status",
            "goals_30", "goals_60", "goals_90",
            "satisfaction_score", "hiring_quality_score",
            "termination_date", "termination_reason", "exit_interview_notes",
            "onboarding_tasks",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "department"]
    search_fields = ["candidate__full_name", "title", "department"]

    def get_queryset(self):
        return Employee.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("candidate", "job").prefetch_related("onboarding_tasks")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["get", "post"])
    def onboarding(self, request, pk=None):
        """List or add onboarding tasks."""
        employee = self.get_object()
        if request.method == "GET":
            tasks = OnboardingTask.objects.filter(
                tenant_id=request.tenant_id, employee=employee
            )
            return Response(OnboardingTaskSerializer(tasks, many=True).data)
        serializer = OnboardingTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.tenant_id, employee=employee)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def complete_task(self, request, pk=None):
        """Mark an onboarding task as complete."""
        from django.utils import timezone
        task_id = request.data.get("task_id")
        task = OnboardingTask.objects.get(id=task_id, employee_id=pk, tenant_id=request.tenant_id)
        task.completed = True
        task.completed_at = timezone.now()
        task.save(update_fields=["completed", "completed_at"])
        return Response(OnboardingTaskSerializer(task).data)


employee_router = DefaultRouter()
employee_router.register("", EmployeeViewSet, basename="employees")

employee_urlpatterns = [
    path("", include(employee_router.urls)),
]


# ══════════════════════════════════════════════════════════════════════════════
# TEAM API (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.accounts.models import User
        model = User
        fields = ["id", "email", "first_name", "last_name", "user_type", "is_active", "created_at"]

class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["user_type", "is_active"]

    def get_queryset(self):
        from apps.accounts.models import User
        return User.objects.filter(tenant_id=self.request.tenant_id)

team_router = DefaultRouter()
team_router.register("", TeamViewSet, basename="team")

team_urlpatterns = [
    path("", include(team_router.urls)),
]


# ══════════════════════════════════════════════════════════════════════════════
# DEBRIEF SESSION API
# ══════════════════════════════════════════════════════════════════════════════

class DebriefSessionSerializer(serializers.ModelSerializer):
    facilitator_name = serializers.CharField(source="facilitator.get_full_name", read_only=True, default="")

    class Meta:
        model = DebriefSession
        fields = [
            "id", "application", "facilitator", "facilitator_name", "participants",
            "scheduled_at", "completed_at", "status", "decision",
            "summary", "action_items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DebriefSessionViewSet(viewsets.ModelViewSet):
    serializer_class = DebriefSessionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["status", "decision", "application"]
    ordering_fields = ["scheduled_at", "created_at"]

    def get_queryset(self):
        return DebriefSession.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("facilitator", "application").prefetch_related("participants")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a debrief as completed with a decision."""
        from django.utils import timezone
        session = self.get_object()
        decision = request.data.get("decision", "pending")
        if decision not in ("advance", "reject", "hold", "pending"):
            return Response({"error": "decision must be advance, reject, hold, or pending"}, status=status.HTTP_400_BAD_REQUEST)
        session.status = "completed"
        session.decision = decision
        session.summary = request.data.get("summary", session.summary)
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "decision", "summary", "completed_at", "updated_at"])
        return Response(DebriefSessionSerializer(session).data)


debrief_router = DefaultRouter()
debrief_router.register("", DebriefSessionViewSet, basename="debrief-sessions")

debrief_urlpatterns = [path("", include(debrief_router.urls))]


# ══════════════════════════════════════════════════════════════════════════════
# CALIBRATION SESSION API
# ══════════════════════════════════════════════════════════════════════════════

class CalibrationSessionSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True, default="")

    class Meta:
        model = CalibrationSession
        fields = [
            "id", "job", "owner", "owner_name", "participants",
            "session_date", "criteria_discussed", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CalibrationSessionViewSet(viewsets.ModelViewSet):
    serializer_class = CalibrationSessionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["job"]
    ordering_fields = ["session_date", "created_at"]

    def get_queryset(self):
        return CalibrationSession.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("owner", "job").prefetch_related("participants")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, owner=self.request.user)


calibration_router = DefaultRouter()
calibration_router.register("", CalibrationSessionViewSet, basename="calibration-sessions")

calibration_urlpatterns = [path("", include(calibration_router.urls))]


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION APPEAL API
# ══════════════════════════════════════════════════════════════════════════════

class ApplicationAppealSerializer(serializers.ModelSerializer):
    raised_by_name = serializers.CharField(source="raised_by.get_full_name", read_only=True, default="")
    reviewer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True, default="")

    class Meta:
        model = ApplicationAppeal
        fields = [
            "id", "application", "raised_by", "raised_by_name",
            "reason", "supporting_evidence", "status",
            "reviewer", "reviewer_name", "reviewer_notes", "resolved_at",
            "ai_decision_overridden", "override_justification",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "raised_by", "created_at", "updated_at"]


class ApplicationAppealViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationAppealSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["status", "application", "ai_decision_overridden"]
    ordering_fields = ["created_at", "resolved_at"]

    def get_queryset(self):
        return ApplicationAppeal.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("raised_by", "reviewer", "application")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, raised_by=self.request.user)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve an appeal with an outcome."""
        from django.utils import timezone
        appeal = self.get_object()
        new_status = request.data.get("status")
        if new_status not in ("upheld", "dismissed", "under_review"):
            return Response({"error": "status must be upheld, dismissed, or under_review"}, status=status.HTTP_400_BAD_REQUEST)
        appeal.status = new_status
        appeal.reviewer = request.user
        appeal.reviewer_notes = request.data.get("reviewer_notes", appeal.reviewer_notes)
        appeal.ai_decision_overridden = request.data.get("ai_decision_overridden", False)
        appeal.override_justification = request.data.get("override_justification", "")
        if new_status in ("upheld", "dismissed"):
            appeal.resolved_at = timezone.now()
        appeal.save()
        return Response(ApplicationAppealSerializer(appeal).data)


appeal_router = DefaultRouter()
appeal_router.register("", ApplicationAppealViewSet, basename="application-appeals")

appeal_urlpatterns = [path("", include(appeal_router.urls))]


# ══════════════════════════════════════════════════════════════════════════════
# HIRING MANAGER NOTE API
# ══════════════════════════════════════════════════════════════════════════════

class HiringManagerNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True, default="")

    class Meta:
        model = HiringManagerNote
        fields = [
            "id", "application", "author", "author_name",
            "content", "is_visible_to_recruiter", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]


class HiringManagerNoteViewSet(viewsets.ModelViewSet):
    serializer_class = HiringManagerNoteSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["application", "is_visible_to_recruiter"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return HiringManagerNote.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("author", "application")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, author=self.request.user)


hm_note_router = DefaultRouter()
hm_note_router.register("", HiringManagerNoteViewSet, basename="hm-notes")

hm_note_urlpatterns = [path("", include(hm_note_router.urls))]



