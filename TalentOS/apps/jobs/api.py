"""API for Jobs app — CRUD + pipeline stage management."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.jobs.models import Job, PipelineStage, JobTemplate, JobIntakeMeeting
from apps.accounts.permissions import IsRecruiter, HasTenantAccess


# ── Serializers ──────────────────────────────────────────────────────────────

class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = [
            "id", "name", "stage_type", "order",
            "is_terminal", "auto_actions",
            "sla_days", "stage_checklist", "notes_template",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class JobSerializer(serializers.ModelSerializer):
    pipeline_stages = PipelineStageSerializer(many=True, read_only=True)
    applicant_count = serializers.SerializerMethodField()
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "title", "slug", "department", "location", "is_remote",
            "employment_type", "description", "requirements",
            "salary_min", "salary_max", "salary_currency",
            "salary_disclosed", "pay_frequency",
            "degree_required", "degree_optional_note",
            "requisition_type",
            "required_skills", "optional_skills", "must_have_skills", "trainable_skills",
            "target_titles",
            "min_years_experience", "max_years_experience", "domain_tags",
            "screening_questions", "status", "published_at", "closed_at",
            "priority", "internal_only", "application_deadline",
            "requisition_id", "headcount_target", "headcount_filled",
            "locations", "view_count",
            "hiring_team", "hiring_manager",
            "sla_days_to_fill", "sla_days_to_screen",
            "target_start_date",
            "jd_quality_score", "inclusive_language_score", "inclusive_language_flags",
            "headcount_plan", "job_level", "job_family",
            "created_by",
            "pipeline_stages", "applicant_count", "applications_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "applicant_count",
                           "applications_count", "headcount_filled", "view_count"]

    def get_applicant_count(self, obj):
        return obj.applications.count()

    def get_applications_count(self, obj):
        return obj.applications.count()


class JobTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobTemplate
        fields = [
            "id", "name", "title", "department", "location",
            "employment_type", "description", "requirements",
            "required_skills", "optional_skills", "target_titles",
            "screening_questions", "pipeline_stages",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "title", "slug", "department", "location", "is_remote",
            "employment_type", "description", "requirements",
            "salary_min", "salary_max", "salary_currency",
            "salary_disclosed", "pay_frequency",
            "degree_required", "degree_optional_note",
            "requisition_type",
            "required_skills", "optional_skills", "must_have_skills", "trainable_skills",
            "target_titles",
            "min_years_experience", "max_years_experience", "domain_tags",
            "screening_questions", "hiring_manager",
            "priority", "internal_only", "application_deadline",
            "requisition_id", "headcount_target", "locations",
            "hiring_team",
            "sla_days_to_fill", "sla_days_to_screen",
            "target_start_date",
            "headcount_plan", "job_level", "job_family",
        ]


class JobIntakeMeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobIntakeMeeting
        fields = [
            "id", "job", "recruiter", "hiring_manager", "meeting_date",
            "notes", "agreed_requirements", "interview_process",
            "target_start_date", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ── ViewSets ─────────────────────────────────────────────────────────────────

class JobIntakeMeetingViewSet(viewsets.ModelViewSet):
    serializer_class = JobIntakeMeetingSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        qs = JobIntakeMeeting.objects.filter(tenant_id=self.request.tenant_id)
        job_id = self.request.query_params.get("job")
        if job_id:
            qs = qs.filter(job_id=job_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

class JobViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "department", "is_remote", "employment_type", "priority"]
    search_fields = ["title", "description", "requisition_id", "department", "location"]
    ordering_fields = ["created_at", "title", "status", "priority", "application_deadline"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobCreateSerializer
        return JobSerializer

    def get_queryset(self):
        return Job.objects.filter(tenant_id=self.request.tenant_id).prefetch_related("pipeline_stages")

    def perform_create(self, serializer):
        job = serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )
        # Create default pipeline stages
        defaults = [
            ("Applied", "applied", 0, False),
            ("Screening", "screening", 1, False),
            ("Interview", "interview", 2, False),
            ("Offer", "offer", 3, False),
            ("Hired", "hired", 4, True),
            ("Rejected", "rejected", 5, True),
        ]
        for name, stype, order, terminal in defaults:
            PipelineStage.objects.create(
                tenant_id=self.request.tenant_id,
                job=job, name=name, stage_type=stype,
                order=order, is_terminal=terminal,
            )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a draft job."""
        from django.utils import timezone
        job = self.get_object()
        if job.status != "draft":
            return Response({"error": "Only draft jobs can be published"}, status=status.HTTP_400_BAD_REQUEST)
        job.status = "open"
        job.published_at = timezone.now()
        job.save(update_fields=["status", "published_at", "updated_at"])
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close a job."""
        from django.utils import timezone
        job = self.get_object()
        job.status = "closed"
        job.closed_at = timezone.now()
        job.save(update_fields=["status", "closed_at", "updated_at"])
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        """Clone a job with all settings."""
        from django.utils.text import slugify
        import time
        job = self.get_object()
        new_title = request.data.get("title", f"{job.title} (Copy)")
        new_job = Job.objects.create(
            tenant_id=request.tenant_id,
            title=new_title,
            slug=slugify(f"{new_title}-{int(time.time())}"),
            department=job.department,
            location=job.location,
            is_remote=job.is_remote,
            employment_type=job.employment_type,
            description=job.description,
            requirements=job.requirements,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            required_skills=job.required_skills,
            optional_skills=job.optional_skills,
            target_titles=job.target_titles,
            screening_questions=job.screening_questions,
            priority=job.priority,
            headcount_target=job.headcount_target,
            template_source=job,
            created_by=request.user,
            hiring_manager=job.hiring_manager,
        )
        # Clone pipeline stages
        for stage in job.pipeline_stages.all():
            PipelineStage.objects.create(
                tenant_id=request.tenant_id,
                job=new_job,
                name=stage.name,
                stage_type=stage.stage_type,
                order=stage.order,
                is_terminal=stage.is_terminal,
                auto_actions=stage.auto_actions,
                sla_days=stage.sla_days,
                stage_checklist=stage.stage_checklist,
                notes_template=stage.notes_template,
            )
        return Response(JobSerializer(new_job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        """Per-job analytics: views, applications, conversion, avg score, time-in-stage."""
        from apps.applications.models import Application
        from django.db.models import Avg, Count
        job = self.get_object()
        apps = Application.objects.filter(job=job, tenant_id=request.tenant_id)
        return Response({
            "total_applications": apps.count(),
            "active": apps.filter(status="active").count(),
            "rejected": apps.filter(status="rejected").count(),
            "hired": apps.filter(status="hired").count(),
            "avg_score": apps.aggregate(avg=Avg("score"))["avg"],
            "view_count": job.view_count,
            "conversion_rate": (apps.filter(status="hired").count() / max(apps.count(), 1)) * 100,
            "headcount_target": job.headcount_target,
            "headcount_filled": job.headcount_filled,
        })


class PipelineStageViewSet(viewsets.ModelViewSet):
    serializer_class = PipelineStageSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return PipelineStage.objects.filter(
            tenant_id=self.request.tenant_id,
            job_id=self.kwargs.get("job_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            job_id=self.kwargs.get("job_pk"),
        )


class JobTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = JobTemplateSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return JobTemplate.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def create_job(self, request, pk=None):
        """Create a new job from this template."""
        from django.utils.text import slugify
        import time
        template = self.get_object()
        job = Job.objects.create(
            tenant_id=request.tenant_id,
            title=request.data.get("title", template.title),
            slug=slugify(f"{template.title}-{int(time.time())}"),
            department=template.department,
            location=template.location,
            employment_type=template.employment_type,
            description=template.description,
            requirements=template.requirements,
            required_skills=template.required_skills,
            optional_skills=template.optional_skills,
            target_titles=template.target_titles,
            screening_questions=template.screening_questions,
            created_by=request.user,
        )
        # Create pipeline stages from template
        for i, stage_data in enumerate(template.pipeline_stages or []):
            PipelineStage.objects.create(
                tenant_id=request.tenant_id,
                job=job,
                name=stage_data.get("name", f"Stage {i}"),
                stage_type=stage_data.get("stage_type", "custom"),
                order=stage_data.get("order", i),
            )
        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)


# ── URLs ─────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("", JobViewSet, basename="jobs")

urlpatterns = [
    path("", include(router.urls)),
    path("templates/", JobTemplateViewSet.as_view({"get": "list", "post": "create"}), name="job-templates"),
    path("templates/<uuid:pk>/", JobTemplateViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="job-template-detail"),
    path("templates/<uuid:pk>/create_job/", JobTemplateViewSet.as_view({"post": "create_job"}), name="job-template-create-job"),
    path("<uuid:job_pk>/stages/", PipelineStageViewSet.as_view({"get": "list", "post": "create"}), name="job-stages"),
    path("<uuid:job_pk>/stages/<uuid:pk>/", PipelineStageViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="job-stage-detail"),
    # Intake meetings
    path("intake-meetings/", JobIntakeMeetingViewSet.as_view({"get": "list", "post": "create"}), name="job-intake-meetings"),
    path("intake-meetings/<uuid:pk>/", JobIntakeMeetingViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="job-intake-meeting-detail"),
]
