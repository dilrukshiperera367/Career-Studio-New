"""
Offer & Compensation Operations — Feature 9
API: ViewSets, Serializers, Custom Actions
Registered at: api/v1/comp-ops/
"""

from django.utils import timezone
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .models import (
    OfferApprovalMatrix,
    CompensationBandGuardrail,
    LocationPayRule,
    SignOnBonusRule,
    RecurringBonusRule,
    EquityGrant,
    RelocationPackage,
    VisaSponsorshipCost,
    InternalEquityCheck,
    PayCompetitivenessWarning,
    OfferVersion,
    CounterOfferPlan,
    OfferApprovalAudit,
    OfferCloseRisk,
    CandidateDecisionDeadline,
    DeclineReasonTaxonomy,
    StructuredClosePlan,
    OfferDocumentBundle,
    CompBenchmarkIntegration,
    PreboardingChecklist,
)


# ──────────────────────────────────────────────────────────────────────────────
# SERIALIZERS
# ──────────────────────────────────────────────────────────────────────────────

class OfferApprovalMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferApprovalMatrix
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class CompensationBandGuardrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompensationBandGuardrail
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class LocationPayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPayRule
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class SignOnBonusRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignOnBonusRule
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class RecurringBonusRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringBonusRule
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class EquityGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquityGrant
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class RelocationPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelocationPackage
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class VisaSponsorshipCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaSponsorshipCost
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InternalEquityCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalEquityCheck
        fields = "__all__"
        read_only_fields = ("id", "reviewed_at", "created_at")


class PayCompetitivenessWarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayCompetitivenessWarning
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class OfferVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferVersion
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class CounterOfferPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterOfferPlan
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class OfferApprovalAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferApprovalAudit
        fields = "__all__"
        read_only_fields = ("id", "actioned_at", "created_at")


class OfferCloseRiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferCloseRisk
        fields = "__all__"
        read_only_fields = ("id", "computed_at")


class CandidateDecisionDeadlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateDecisionDeadline
        fields = "__all__"
        read_only_fields = ("id", "reminder_sent_at", "final_reminder_sent_at", "decided_at", "created_at")


class DeclineReasonTaxonomySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeclineReasonTaxonomy
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class StructuredClosePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = StructuredClosePlan
        fields = "__all__"
        read_only_fields = ("id", "closed_at", "created_at", "updated_at")


class OfferDocumentBundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferDocumentBundle
        fields = "__all__"
        read_only_fields = ("id", "generated_at", "sent_at", "signed_at", "created_at")


class CompBenchmarkIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompBenchmarkIntegration
        fields = "__all__"
        read_only_fields = ("id", "last_synced_at", "created_at", "updated_at")


class PreboardingChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreboardingChecklist
        fields = "__all__"
        read_only_fields = ("id", "kickoff_triggered_at", "created_at", "updated_at")


# ──────────────────────────────────────────────────────────────────────────────
# VIEWSETS
# ──────────────────────────────────────────────────────────────────────────────

class OfferApprovalMatrixViewSet(viewsets.ModelViewSet):
    serializer_class = OfferApprovalMatrixSerializer

    def get_queryset(self):
        return OfferApprovalMatrix.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class CompensationBandGuardrailViewSet(viewsets.ModelViewSet):
    serializer_class = CompensationBandGuardrailSerializer

    def get_queryset(self):
        return CompensationBandGuardrail.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class LocationPayRuleViewSet(viewsets.ModelViewSet):
    serializer_class = LocationPayRuleSerializer

    def get_queryset(self):
        return LocationPayRule.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class SignOnBonusRuleViewSet(viewsets.ModelViewSet):
    serializer_class = SignOnBonusRuleSerializer

    def get_queryset(self):
        return SignOnBonusRule.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class RecurringBonusRuleViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringBonusRuleSerializer

    def get_queryset(self):
        return RecurringBonusRule.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class EquityGrantViewSet(viewsets.ModelViewSet):
    serializer_class = EquityGrantSerializer

    def get_queryset(self):
        return EquityGrant.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class RelocationPackageViewSet(viewsets.ModelViewSet):
    serializer_class = RelocationPackageSerializer

    def get_queryset(self):
        return RelocationPackage.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class VisaSponsorshipCostViewSet(viewsets.ModelViewSet):
    serializer_class = VisaSponsorshipCostSerializer

    def get_queryset(self):
        return VisaSponsorshipCost.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class InternalEquityCheckViewSet(viewsets.ModelViewSet):
    serializer_class = InternalEquityCheckSerializer

    def get_queryset(self):
        return InternalEquityCheck.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        """Raise an equity flag on this check."""
        check = self.get_object()
        check.flag_raised = True
        check.flag_reason = request.data.get("flag_reason", "")
        check.save(update_fields=["flag_raised", "flag_reason"])
        return Response(InternalEquityCheckSerializer(check).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark this equity check as reviewed."""
        check = self.get_object()
        check.reviewed_by = request.user
        check.reviewed_at = timezone.now()
        check.save(update_fields=["reviewed_by", "reviewed_at"])
        return Response(InternalEquityCheckSerializer(check).data)


class PayCompetitivenessWarningViewSet(viewsets.ModelViewSet):
    serializer_class = PayCompetitivenessWarningSerializer

    def get_queryset(self):
        return PayCompetitivenessWarning.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class OfferVersionViewSet(viewsets.ModelViewSet):
    serializer_class = OfferVersionSerializer

    def get_queryset(self):
        return OfferVersion.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_current(self, request, pk=None):
        """Mark this offer version as the active/current version."""
        version = self.get_object()
        # Deactivate siblings for same offer_id by bumping version metadata via details
        OfferVersion.objects.filter(
            tenant=self.request.tenant_id,
            offer_id=version.offer_id,
        ).exclude(pk=version.pk).update(
            details={**{}, "is_current": False}
        )
        version.details = {**version.details, "is_current": True}
        version.save(update_fields=["details"])
        return Response(OfferVersionSerializer(version).data)


class CounterOfferPlanViewSet(viewsets.ModelViewSet):
    serializer_class = CounterOfferPlanSerializer

    def get_queryset(self):
        return CounterOfferPlan.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def set_outcome(self, request, pk=None):
        """Record the outcome of a counteroffer negotiation."""
        plan = self.get_object()
        outcome = request.data.get("outcome", "")
        outcome_notes = request.data.get("outcome_notes", "")
        plan.outcome = outcome
        plan.outcome_notes = outcome_notes
        plan.save(update_fields=["outcome", "outcome_notes"])
        return Response(CounterOfferPlanSerializer(plan).data)


class OfferApprovalAuditViewSet(viewsets.ModelViewSet):
    serializer_class = OfferApprovalAuditSerializer

    def get_queryset(self):
        return OfferApprovalAudit.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.tenant_id,
            approver=self.request.user,
            actioned_at=timezone.now(),
        )

    @action(detail=False, methods=["post"])
    def record_action(self, request):
        """Record an approval step action in the audit trail."""
        offer_version_id = request.data.get("offer_version_id")
        if not offer_version_id:
            return Response({"detail": "offer_version_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        audit = OfferApprovalAudit.objects.create(
            tenant=self.request.tenant_id,
            offer_version_id=offer_version_id,
            approver=request.user,
            approval_step=request.data.get("approval_step", 1),
            action=request.data.get("action", "pending"),
            note=request.data.get("note", ""),
            actioned_at=timezone.now(),
        )
        return Response(OfferApprovalAuditSerializer(audit).data, status=status.HTTP_201_CREATED)


class OfferCloseRiskViewSet(viewsets.ModelViewSet):
    serializer_class = OfferCloseRiskSerializer

    def get_queryset(self):
        return OfferCloseRisk.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=False, methods=["post"])
    def compute(self, request):
        """Compute and save a new offer close risk score."""
        offer_version_id = request.data.get("offer_version_id")
        if not offer_version_id:
            return Response({"detail": "offer_version_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        risk = OfferCloseRisk.objects.create(
            tenant=self.request.tenant_id,
            offer_version_id=offer_version_id,
            candidate_name=request.data.get("candidate_name", ""),
            risk_score=request.data.get("risk_score", 0),
            risk_level=request.data.get("risk_level", "low"),
            risk_factors=request.data.get("risk_factors", []),
            recommended_close_actions=request.data.get("recommended_close_actions", []),
        )
        return Response(OfferCloseRiskSerializer(risk).data, status=status.HTTP_201_CREATED)


class CandidateDecisionDeadlineViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateDecisionDeadlineSerializer

    def get_queryset(self):
        return CandidateDecisionDeadline.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        """Extend a candidate's decision deadline."""
        deadline = self.get_object()
        extended_deadline = request.data.get("extended_deadline")
        if not extended_deadline:
            return Response({"detail": "extended_deadline is required"}, status=status.HTTP_400_BAD_REQUEST)

        deadline.extended = True
        deadline.extended_deadline = extended_deadline
        deadline.extension_reason = request.data.get("extension_reason", "")
        deadline.save(update_fields=["extended", "extended_deadline", "extension_reason"])
        return Response(CandidateDecisionDeadlineSerializer(deadline).data)


class DeclineReasonTaxonomyViewSet(viewsets.ModelViewSet):
    serializer_class = DeclineReasonTaxonomySerializer

    def get_queryset(self):
        return DeclineReasonTaxonomy.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class StructuredClosePlanViewSet(viewsets.ModelViewSet):
    serializer_class = StructuredClosePlanSerializer

    def get_queryset(self):
        return StructuredClosePlan.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, close_owner=self.request.user)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close the structured close plan with a final outcome."""
        plan = self.get_object()
        plan.status = request.data.get("status", "closed")
        plan.closed_at = timezone.now()
        plan.outcome = request.data.get("outcome", "")
        plan.save(update_fields=["status", "closed_at", "outcome"])
        return Response(StructuredClosePlanSerializer(plan).data)


class OfferDocumentBundleViewSet(viewsets.ModelViewSet):
    serializer_class = OfferDocumentBundleSerializer

    def get_queryset(self):
        return OfferDocumentBundle.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """Mark the document bundle as generated."""
        bundle = self.get_object()
        bundle.generated_at = timezone.now()
        bundle.status = "generated"
        bundle.save(update_fields=["generated_at", "status"])
        return Response(OfferDocumentBundleSerializer(bundle).data)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Mark the document bundle as sent to the candidate."""
        bundle = self.get_object()
        bundle.sent_at = timezone.now()
        bundle.status = "sent"
        bundle.save(update_fields=["sent_at", "status"])
        return Response(OfferDocumentBundleSerializer(bundle).data)


class CompBenchmarkIntegrationViewSet(viewsets.ModelViewSet):
    serializer_class = CompBenchmarkIntegrationSerializer

    def get_queryset(self):
        return CompBenchmarkIntegration.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """Trigger a sync with the benchmark data provider."""
        integration = self.get_object()
        integration.last_synced_at = timezone.now()
        # Accept optional updated snapshot from caller
        if "data_snapshot" in request.data:
            integration.data_snapshot = request.data["data_snapshot"]
        integration.save(update_fields=["last_synced_at", "data_snapshot"])
        return Response(CompBenchmarkIntegrationSerializer(integration).data)


class PreboardingChecklistViewSet(viewsets.ModelViewSet):
    serializer_class = PreboardingChecklistSerializer

    def get_queryset(self):
        return PreboardingChecklist.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def kick_off(self, request, pk=None):
        """Trigger the preboarding checklist kickoff."""
        checklist = self.get_object()
        checklist.kickoff_triggered_at = timezone.now()
        checklist.save(update_fields=["kickoff_triggered_at"])
        return Response(PreboardingChecklistSerializer(checklist).data)


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER & URL PATTERNS
# ──────────────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register(r"approval-matrices", OfferApprovalMatrixViewSet, basename="comp-approval-matrix")
router.register(r"band-guardrails", CompensationBandGuardrailViewSet, basename="comp-band-guardrail")
router.register(r"location-pay-rules", LocationPayRuleViewSet, basename="comp-location-pay-rule")
router.register(r"sign-on-rules", SignOnBonusRuleViewSet, basename="comp-sign-on-rule")
router.register(r"recurring-bonus-rules", RecurringBonusRuleViewSet, basename="comp-recurring-bonus")
router.register(r"equity-grants", EquityGrantViewSet, basename="comp-equity-grant")
router.register(r"relocation-packages", RelocationPackageViewSet, basename="comp-relocation")
router.register(r"visa-costs", VisaSponsorshipCostViewSet, basename="comp-visa-cost")
router.register(r"equity-checks", InternalEquityCheckViewSet, basename="comp-equity-check")
router.register(r"pay-warnings", PayCompetitivenessWarningViewSet, basename="comp-pay-warning")
router.register(r"offer-versions", OfferVersionViewSet, basename="comp-offer-version")
router.register(r"counteroffer-plans", CounterOfferPlanViewSet, basename="comp-counteroffer-plan")
router.register(r"approval-audits", OfferApprovalAuditViewSet, basename="comp-approval-audit")
router.register(r"close-risks", OfferCloseRiskViewSet, basename="comp-close-risk")
router.register(r"decision-deadlines", CandidateDecisionDeadlineViewSet, basename="comp-decision-deadline")
router.register(r"decline-reasons", DeclineReasonTaxonomyViewSet, basename="comp-decline-reason")
router.register(r"close-plans", StructuredClosePlanViewSet, basename="comp-close-plan")
router.register(r"document-bundles", OfferDocumentBundleViewSet, basename="comp-document-bundle")
router.register(r"benchmark-integrations", CompBenchmarkIntegrationViewSet, basename="comp-benchmark")
router.register(r"preboarding-checklists", PreboardingChecklistViewSet, basename="comp-preboarding")

urlpatterns = router.urls
