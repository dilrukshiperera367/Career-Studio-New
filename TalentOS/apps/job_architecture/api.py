"""API for Job Architecture app — job families, levels, competencies, headcount, salary bands,
hiring team templates, SLA configs, intake meeting templates, and hiring plan calendars."""

import re
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.job_architecture.models import (
    JobFamily, JobLevel, CompetencyFramework, Competency,
    HeadcountPlan, HeadcountRequisition, SalaryBand,
    JobDescriptionVersion, ApprovalChain, ApprovalStep,
    HiringTeamTemplate, SLAConfig, IntakeMeetingTemplate, HiringPlanCalendar,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess


# ── Inclusive Language Scanner ────────────────────────────────────────────────
# A lightweight rule-based scanner. Replace with an ML service if desired.

INCLUSIVE_LANGUAGE_RULES = [
    # Gendered / exclusionary terms → neutral alternatives
    {"pattern": r"\bninja\b", "suggestion": "engineer / specialist", "severity": "medium"},
    {"pattern": r"\brock ?star\b", "suggestion": "top performer / expert", "severity": "medium"},
    {"pattern": r"\bguru\b", "suggestion": "expert / specialist", "severity": "low"},
    {"pattern": r"\bmanpower\b", "suggestion": "workforce / staff", "severity": "high"},
    {"pattern": r"\bmanned\b", "suggestion": "staffed / operated", "severity": "medium"},
    {"pattern": r"\bhe or she\b", "suggestion": "they", "severity": "low"},
    {"pattern": r"\bhis/her\b", "suggestion": "their", "severity": "low"},
    {"pattern": r"\bseminal\b", "suggestion": "foundational / influential", "severity": "low"},
    {"pattern": r"\bblackout\b", "suggestion": "scheduled downtime", "severity": "low"},
    {"pattern": r"\bmaster\b", "suggestion": "primary / main", "severity": "low"},
    {"pattern": r"\bwhitelist\b", "suggestion": "allowlist", "severity": "low"},
    {"pattern": r"\bblacklist\b", "suggestion": "denylist", "severity": "low"},
    {"pattern": r"\bcultural fit\b", "suggestion": "values alignment / culture add", "severity": "high"},
    {"pattern": r"\bclean[- ]shaven\b", "suggestion": "professional appearance", "severity": "high"},
    {"pattern": r"\bnative (english )?speaker\b", "suggestion": "fluent English speaker", "severity": "high"},
    {"pattern": r"\byoung and dynamic\b", "suggestion": "energetic / motivated", "severity": "high"},
    {"pattern": r"\brecent graduate\b", "suggestion": "early-career candidate", "severity": "medium"},
    {"pattern": r"\bdigital native\b", "suggestion": "tech-savvy professional", "severity": "medium"},
]

# JD quality heuristics
JD_QUALITY_CHECKS = [
    ("has_about_section", r"about (the role|us|this position)", 10),
    ("has_responsibilities", r"(responsibilit|what you.ll do|your role)", 20),
    ("has_requirements", r"(requirement|what we.re looking for|qualifications)", 20),
    ("has_benefits", r"(benefit|perk|we offer|compensation)", 10),
    ("reasonable_length", None, 15),   # handled programmatically
    ("no_walls_of_text", None, 10),    # handled programmatically
    ("has_salary_info", r"(\$[\d,]+|salary|compensation range|pay range)", 15),
]


def scan_jd(text: str):
    """Run inclusive language scan and quality score on a JD text block."""
    lower = text.lower()

    # ── Inclusive language ────────────────────────────────────────────────────
    flags = []
    for rule in INCLUSIVE_LANGUAGE_RULES:
        if re.search(rule["pattern"], lower):
            flags.append({
                "term": re.search(rule["pattern"], lower).group(),
                "suggestion": rule["suggestion"],
                "severity": rule["severity"],
            })

    high = sum(1 for f in flags if f["severity"] == "high")
    medium = sum(1 for f in flags if f["severity"] == "medium")
    low = sum(1 for f in flags if f["severity"] == "low")
    inclusive_score = max(0.0, 100.0 - (high * 20 + medium * 10 + low * 5))

    # ── JD Quality ────────────────────────────────────────────────────────────
    quality_score = 0.0
    for name, pattern, points in JD_QUALITY_CHECKS:
        if pattern and re.search(pattern, lower):
            quality_score += points
        elif name == "reasonable_length":
            word_count = len(text.split())
            if 200 <= word_count <= 1200:
                quality_score += points
            elif 100 <= word_count < 200 or 1200 < word_count <= 2000:
                quality_score += points / 2
        elif name == "no_walls_of_text":
            paragraphs = [p for p in text.split("\n\n") if p.strip()]
            avg_para_words = sum(len(p.split()) for p in paragraphs) / max(len(paragraphs), 1)
            if avg_para_words < 80:
                quality_score += points

    quality_score = min(quality_score, 100.0)

    return {
        "inclusive_language_score": round(inclusive_score, 1),
        "jd_quality_score": round(quality_score, 1),
        "inclusive_language_flags": flags,
        "word_count": len(text.split()),
        "flag_count": len(flags),
    }


# ── Serializers ───────────────────────────────────────────────────────────────

class JobFamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobFamily
        fields = ["id", "name", "code", "description", "parent", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLevel
        fields = ["id", "job_family", "name", "code", "level_type", "numeric_level", "scope", "created_at"]
        read_only_fields = ["id", "created_at"]


class CompetencyFrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetencyFramework
        fields = ["id", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = ["id", "framework", "name", "description", "category", "required_for_levels", "created_at"]
        read_only_fields = ["id", "created_at"]


class HeadcountRequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeadcountRequisition
        fields = [
            "id", "plan", "job_family", "job_level", "title", "department", "location",
            "target_start_date", "status", "linked_job", "notes", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class HeadcountPlanSerializer(serializers.ModelSerializer):
    requisitions = HeadcountRequisitionSerializer(many=True, read_only=True)

    class Meta:
        model = HeadcountPlan
        fields = [
            "id", "name", "fiscal_year", "quarter", "department", "owner",
            "status", "total_headcount", "approved_headcount", "notes",
            "requisitions", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SalaryBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryBand
        fields = [
            "id", "job_family", "job_level", "currency",
            "pay_range_min", "pay_range_mid", "pay_range_max",
            "effective_date", "expiry_date", "geo_zone",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobDescriptionVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescriptionVersion
        fields = [
            "id", "job", "version_number", "title", "description", "requirements",
            "inclusive_language_score", "jd_quality_score", "inclusive_language_flags",
            "created_by", "is_current", "created_at",
        ]
        read_only_fields = ["id", "created_at", "version_number"]


class ApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalStep
        fields = ["id", "chain", "order", "approver", "approver_role", "is_required", "timeout_hours", "created_at"]
        read_only_fields = ["id", "created_at"]


class ApprovalChainSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalChain
        fields = ["id", "name", "chain_type", "is_active", "steps", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class HiringTeamTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiringTeamTemplate
        fields = [
            "id", "name", "job_family", "recruiter", "coordinator",
            "interviewers", "notes", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SLAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAConfig
        fields = [
            "id", "name", "scope", "job_family", "job_level", "department",
            "days_to_fill", "days_to_screen", "days_to_offer", "days_per_stage",
            "escalation_enabled", "escalation_recipient_role", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class IntakeMeetingTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntakeMeetingTemplate
        fields = [
            "id", "name", "job_family", "agenda_items", "recruiter_questions",
            "must_have_prompt", "nice_to_have_prompt", "suggested_pipeline",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class HiringPlanCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiringPlanCalendar
        fields = [
            "id", "plan", "requisition", "fiscal_year", "quarter", "month",
            "department", "location", "hiring_manager", "target_start_date",
            "headcount", "budget_allocated", "budget_currency", "status", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class JobFamilyViewSet(viewsets.ModelViewSet):
    serializer_class = JobFamilySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return JobFamily.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class JobLevelViewSet(viewsets.ModelViewSet):
    serializer_class = JobLevelSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job_family", "level_type"]

    def get_queryset(self):
        return JobLevel.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class CompetencyFrameworkViewSet(viewsets.ModelViewSet):
    serializer_class = CompetencyFrameworkSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return CompetencyFramework.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class CompetencyViewSet(viewsets.ModelViewSet):
    serializer_class = CompetencySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["framework", "category"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return Competency.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class HeadcountPlanViewSet(viewsets.ModelViewSet):
    serializer_class = HeadcountPlanSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "fiscal_year", "department"]

    def get_queryset(self):
        return HeadcountPlan.objects.filter(tenant_id=self.request.tenant_id).prefetch_related("requisitions")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        plan = self.get_object()
        plan.status = "approved"
        plan.save(update_fields=["status"])
        return Response(HeadcountPlanSerializer(plan).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        plan = self.get_object()
        plan.status = "submitted"
        plan.save(update_fields=["status"])
        return Response(HeadcountPlanSerializer(plan).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        plan = self.get_object()
        plan.status = "rejected"
        plan.save(update_fields=["status"])
        return Response(HeadcountPlanSerializer(plan).data)

    @action(detail=False, methods=["get"])
    def by_quarter(self, request):
        """Return headcount totals grouped by fiscal year + quarter."""
        fy = request.query_params.get("fiscal_year")
        qs = self.get_queryset()
        if fy:
            qs = qs.filter(fiscal_year=fy)
        result = {}
        for plan in qs:
            key = f"FY{plan.fiscal_year} Q{plan.quarter or 'Annual'}"
            result.setdefault(key, {"plans": 0, "total_headcount": 0, "approved_headcount": 0})
            result[key]["plans"] += 1
            result[key]["total_headcount"] += plan.total_headcount
            result[key]["approved_headcount"] += plan.approved_headcount
        return Response(result)


class HeadcountRequisitionViewSet(viewsets.ModelViewSet):
    serializer_class = HeadcountRequisitionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["plan", "status"]

    def get_queryset(self):
        return HeadcountRequisition.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class SalaryBandViewSet(viewsets.ModelViewSet):
    serializer_class = SalaryBandSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job_family", "job_level", "currency", "geo_zone"]

    def get_queryset(self):
        return SalaryBand.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=["get"])
    def lookup(self, request):
        """Quick look-up: return the active band for a family + level + geo combo."""
        from django.utils import timezone
        family_id = request.query_params.get("job_family")
        level_id = request.query_params.get("job_level")
        geo = request.query_params.get("geo_zone", "")
        today = timezone.now().date()
        qs = self.get_queryset().filter(
            effective_date__lte=today,
        ).filter(
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gte=today)
        )
        if family_id:
            qs = qs.filter(job_family_id=family_id)
        if level_id:
            qs = qs.filter(job_level_id=level_id)
        if geo:
            qs = qs.filter(geo_zone__icontains=geo)
        band = qs.first()
        if not band:
            return Response({"detail": "No active salary band found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SalaryBandSerializer(band).data)


class JobDescriptionVersionViewSet(viewsets.ModelViewSet):
    serializer_class = JobDescriptionVersionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job", "is_current"]

    def get_queryset(self):
        return JobDescriptionVersion.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        from apps.job_architecture.models import JobDescriptionVersion as JDV
        job_id = serializer.validated_data.get("job").id
        last = JDV.objects.filter(tenant_id=self.request.tenant_id, job_id=job_id).order_by("-version_number").first()
        next_version = (last.version_number + 1) if last else 1
        JDV.objects.filter(tenant_id=self.request.tenant_id, job_id=job_id).update(is_current=False)
        # Auto-run JD scan on creation
        full_text = f"{serializer.validated_data.get('title', '')} {serializer.validated_data.get('description', '')} {serializer.validated_data.get('requirements', '')}"
        scan_result = scan_jd(full_text)
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
            version_number=next_version,
            inclusive_language_score=scan_result["inclusive_language_score"],
            jd_quality_score=scan_result["jd_quality_score"],
            inclusive_language_flags=scan_result["inclusive_language_flags"],
        )

    @action(detail=True, methods=["post"])
    def scan(self, request, pk=None):
        """Re-run inclusive language + quality scan on this JD version."""
        jd = self.get_object()
        full_text = f"{jd.title} {jd.description} {jd.requirements}"
        result = scan_jd(full_text)
        jd.inclusive_language_score = result["inclusive_language_score"]
        jd.jd_quality_score = result["jd_quality_score"]
        jd.inclusive_language_flags = result["inclusive_language_flags"]
        jd.save(update_fields=["inclusive_language_score", "jd_quality_score", "inclusive_language_flags"])
        return Response({**JobDescriptionVersionSerializer(jd).data, **result})

    @action(detail=False, methods=["post"])
    def preview_scan(self, request):
        """Scan arbitrary JD text without saving — used in the JD builder UI."""
        text = request.data.get("text", "")
        if not text:
            return Response({"error": "text is required"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(scan_jd(text))


class ApprovalChainViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalChainSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["chain_type", "is_active"]

    def get_queryset(self):
        return ApprovalChain.objects.filter(tenant_id=self.request.tenant_id).prefetch_related("steps")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class ApprovalStepViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalStepSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return ApprovalStep.objects.filter(
            tenant_id=self.request.tenant_id,
            chain_id=self.kwargs.get("chain_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            chain_id=self.kwargs.get("chain_pk"),
        )


class HiringTeamTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = HiringTeamTemplateSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job_family", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return HiringTeamTemplate.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def apply_to_job(self, request, pk=None):
        """Apply this hiring team template to a job."""
        from apps.jobs.models import Job
        template = self.get_object()
        job_id = request.data.get("job_id")
        try:
            job = Job.objects.get(id=job_id, tenant_id=request.tenant_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        # Build hiring_team JSON from template
        team = []
        if template.recruiter_id:
            team.append({"user_id": str(template.recruiter_id), "role": "recruiter"})
        if template.coordinator_id:
            team.append({"user_id": str(template.coordinator_id), "role": "coordinator"})
        for interviewer in (template.interviewers or []):
            team.append({**interviewer, "role": "interviewer"})
        job.hiring_team = team
        if template.recruiter_id:
            job.hiring_manager = template.recruiter
        job.save(update_fields=["hiring_team", "hiring_manager"])
        return Response({"job_id": str(job.id), "hiring_team": team})


class SLAConfigViewSet(viewsets.ModelViewSet):
    serializer_class = SLAConfigSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["scope", "job_family", "job_level", "is_active"]

    def get_queryset(self):
        return SLAConfig.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=["get"])
    def resolve(self, request):
        """Return the most specific SLA config for a given job_family / job_level / dept."""
        family_id = request.query_params.get("job_family")
        level_id = request.query_params.get("job_level")
        dept = request.query_params.get("department", "")
        qs = self.get_queryset().filter(is_active=True)
        # Priority: job_level > job_family > department > global
        if level_id:
            cfg = qs.filter(scope="job_level", job_level_id=level_id).first()
            if cfg:
                return Response(SLAConfigSerializer(cfg).data)
        if family_id:
            cfg = qs.filter(scope="job_family", job_family_id=family_id).first()
            if cfg:
                return Response(SLAConfigSerializer(cfg).data)
        if dept:
            cfg = qs.filter(scope="department", department__iexact=dept).first()
            if cfg:
                return Response(SLAConfigSerializer(cfg).data)
        cfg = qs.filter(scope="global").first()
        if cfg:
            return Response(SLAConfigSerializer(cfg).data)
        return Response({"detail": "No SLA config found."}, status=status.HTTP_404_NOT_FOUND)


class IntakeMeetingTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = IntakeMeetingTemplateSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job_family", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return IntakeMeetingTemplate.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class HiringPlanCalendarViewSet(viewsets.ModelViewSet):
    serializer_class = HiringPlanCalendarSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["plan", "fiscal_year", "quarter", "department", "status", "hiring_manager"]

    def get_queryset(self):
        return HiringPlanCalendar.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Aggregated hiring plan calendar summary by FY + quarter."""
        fy = request.query_params.get("fiscal_year")
        qs = self.get_queryset()
        if fy:
            qs = qs.filter(fiscal_year=fy)
        result = {}
        for entry in qs:
            key = f"FY{entry.fiscal_year} Q{entry.quarter}"
            result.setdefault(key, {
                "entries": 0, "headcount": 0, "budget_allocated": 0,
                "departments": set(),
            })
            result[key]["entries"] += 1
            result[key]["headcount"] += entry.headcount
            if entry.budget_allocated:
                result[key]["budget_allocated"] += float(entry.budget_allocated)
            if entry.department:
                result[key]["departments"].add(entry.department)
        # Convert sets to lists for JSON serialisation
        for k in result:
            result[k]["departments"] = list(result[k]["departments"])
        return Response(result)


# ── Needed for SalaryBandViewSet.lookup ──────────────────────────────────────
from django.db import models  # noqa: E402 — imported after class definitions intentionally


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("families", JobFamilyViewSet, basename="job-families")
router.register("levels", JobLevelViewSet, basename="job-levels")
router.register("frameworks", CompetencyFrameworkViewSet, basename="competency-frameworks")
router.register("competencies", CompetencyViewSet, basename="competencies")
router.register("headcount-plans", HeadcountPlanViewSet, basename="headcount-plans")
router.register("headcount-requisitions", HeadcountRequisitionViewSet, basename="headcount-requisitions")
router.register("salary-bands", SalaryBandViewSet, basename="salary-bands")
router.register("jd-versions", JobDescriptionVersionViewSet, basename="jd-versions")
router.register("approval-chains", ApprovalChainViewSet, basename="approval-chains")
router.register("hiring-team-templates", HiringTeamTemplateViewSet, basename="hiring-team-templates")
router.register("sla-configs", SLAConfigViewSet, basename="sla-configs")
router.register("intake-templates", IntakeMeetingTemplateViewSet, basename="intake-templates")
router.register("hiring-calendar", HiringPlanCalendarViewSet, basename="hiring-calendar")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "approval-chains/<uuid:chain_pk>/steps/",
        ApprovalStepViewSet.as_view({"get": "list", "post": "create"}),
        name="approval-steps",
    ),
    path(
        "approval-chains/<uuid:chain_pk>/steps/<uuid:pk>/",
        ApprovalStepViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="approval-step-detail",
    ),
]
