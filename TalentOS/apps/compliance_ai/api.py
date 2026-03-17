"""API for Compliance AI app — EU AI Act Annex III: prompt logs, human review, bias monitoring, DPIA."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.compliance_ai.models import (
    AIModel,
    AIPromptLog,
    AIOutputLog,
    HumanReviewQueue,
    AIOverrideRecord,
    BiasMonitoringReport,
    DPIATemplate,
    DPIAAssessment,
    AIPolicy,
    CandidateAppeal,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess, IsTenantAdmin


# ── Serializers ───────────────────────────────────────────────────────────────

class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class AIPromptLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIPromptLog
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class AIOutputLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIOutputLog
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class HumanReviewQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = HumanReviewQueue
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class AIOverrideRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIOverrideRecord
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class BiasMonitoringReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiasMonitoringReport
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class DPIATemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DPIATemplate
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class DPIAAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DPIAAssessment
        fields = "__all__"
        read_only_fields = ["id", "tenant", "approved_at", "created_at", "updated_at"]


class AIPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIPolicy
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class CandidateAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateAppeal
        fields = "__all__"
        read_only_fields = ["id", "tenant", "resolved_at", "created_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class AIModelViewSet(viewsets.ModelViewSet):
    serializer_class = AIModelSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["risk_level", "is_active"]

    def get_queryset(self):
        return AIModel.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class AIPromptLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AIPromptLogSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["ai_model"]

    def get_queryset(self):
        return AIPromptLog.objects.filter(tenant_id=self.request.tenant_id).select_related("ai_model")


class AIOutputLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AIOutputLogSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["flagged_for_review"]

    def get_queryset(self):
        return AIOutputLog.objects.filter(tenant_id=self.request.tenant_id)


class HumanReviewQueueViewSet(viewsets.ModelViewSet):
    serializer_class = HumanReviewQueueSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "object_type"]

    def get_queryset(self):
        return HumanReviewQueue.objects.filter(tenant_id=self.request.tenant_id).select_related("output_log")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Mark an AI output as approved by a human reviewer."""
        from django.utils import timezone
        item = self.get_object()
        item.status = "approved"
        item.reviewer = request.user
        item.reviewer_notes = request.data.get("reviewer_notes", "")
        item.reviewed_at = timezone.now()
        item.save(update_fields=["status", "reviewer", "reviewer_notes", "reviewed_at"])
        return Response(HumanReviewQueueSerializer(item).data)

    @action(detail=True, methods=["post"])
    def override(self, request, pk=None):
        """Record a human override of the AI decision. Creates an AIOverrideRecord."""
        from django.utils import timezone
        item = self.get_object()
        item.status = "overridden"
        item.reviewer = request.user
        item.reviewed_at = timezone.now()
        item.reviewer_notes = request.data.get("reviewer_notes", "")
        item.save(update_fields=["status", "reviewer", "reviewed_at", "reviewer_notes"])

        AIOverrideRecord.objects.create(
            tenant_id=self.request.tenant_id,
            review_item=item,
            ai_decision=request.data.get("ai_decision", ""),
            human_decision=request.data.get("human_decision", ""),
            override_reason=request.data.get("override_reason", ""),
            override_category=request.data.get("override_category", ""),
            overridden_by=request.user,
        )
        return Response(HumanReviewQueueSerializer(item).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        """Escalate a review item to a senior reviewer."""
        item = self.get_object()
        item.status = "escalated"
        item.save(update_fields=["status"])
        return Response(HumanReviewQueueSerializer(item).data)


class AIOverrideRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AIOverrideRecordSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]

    def get_queryset(self):
        return AIOverrideRecord.objects.filter(tenant_id=self.request.tenant_id)


class BiasMonitoringReportViewSet(viewsets.ModelViewSet):
    serializer_class = BiasMonitoringReportSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["ai_model"]

    def get_queryset(self):
        return BiasMonitoringReport.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class DPIATemplateViewSet(viewsets.ModelViewSet):
    serializer_class = DPIATemplateSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]

    def get_queryset(self):
        return DPIATemplate.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class DPIAAssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = DPIAAssessmentSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["status", "ai_model"]

    def get_queryset(self):
        return DPIAAssessment.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft DPIA for DPO review."""
        assessment = self.get_object()
        if assessment.status != "draft":
            return Response({"error": "Only draft DPIAs can be submitted."}, status=status.HTTP_400_BAD_REQUEST)
        assessment.status = "submitted"
        assessment.save(update_fields=["status", "updated_at"])
        return Response(DPIAAssessmentSerializer(assessment).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """DPO approves a submitted DPIA."""
        from django.utils import timezone
        assessment = self.get_object()
        assessment.status = "approved"
        assessment.dpo_reviewer = request.user
        assessment.approved_at = timezone.now()
        assessment.save(update_fields=["status", "dpo_reviewer", "approved_at", "updated_at"])
        return Response(DPIAAssessmentSerializer(assessment).data)


class AIPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = AIPolicySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]

    def get_queryset(self):
        return AIPolicy.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CandidateAppealViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateAppealSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status"]

    def get_queryset(self):
        return CandidateAppeal.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def uphold(self, request, pk=None):
        """Uphold a candidate appeal — decision reversed."""
        from django.utils import timezone
        appeal = self.get_object()
        appeal.status = "upheld"
        appeal.reviewer = request.user
        appeal.outcome_notes = request.data.get("outcome_notes", "")
        appeal.resolved_at = timezone.now()
        appeal.save(update_fields=["status", "reviewer", "outcome_notes", "resolved_at"])
        return Response(CandidateAppealSerializer(appeal).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        """Dismiss a candidate appeal — original decision stands."""
        from django.utils import timezone
        appeal = self.get_object()
        appeal.status = "dismissed"
        appeal.reviewer = request.user
        appeal.outcome_notes = request.data.get("outcome_notes", "")
        appeal.resolved_at = timezone.now()
        appeal.save(update_fields=["status", "reviewer", "outcome_notes", "resolved_at"])
        return Response(CandidateAppealSerializer(appeal).data)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("models", AIModelViewSet, basename="ai-models")
router.register("prompt-logs", AIPromptLogViewSet, basename="ai-prompt-logs")
router.register("output-logs", AIOutputLogViewSet, basename="ai-output-logs")
router.register("review-queue", HumanReviewQueueViewSet, basename="human-review-queue")
router.register("overrides", AIOverrideRecordViewSet, basename="ai-overrides")
router.register("bias-reports", BiasMonitoringReportViewSet, basename="bias-reports")
router.register("dpia-templates", DPIATemplateViewSet, basename="dpia-templates")
router.register("dpia-assessments", DPIAAssessmentViewSet, basename="dpia-assessments")
router.register("policy", AIPolicyViewSet, basename="ai-policy")
router.register("appeals", CandidateAppealViewSet, basename="candidate-appeals")

urlpatterns = [
    path("", include(router.urls)),
]
