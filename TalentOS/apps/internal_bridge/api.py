"""
Internal Recruiting Bridge — Feature 10
API: ViewSets, Serializers, Custom Actions
Registered at: api/v1/bridge/
"""

from django.utils import timezone
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .models import (
    InternalRequisition,
    InternalPostingWindow,
    InternalCandidate,
    InternalTransferWorkflow,
    EmployeeSkillProfileBridge,
    InternalReferral,
    RehireAlumniRecord,
    PipelineComparison,
    InternalCandidateCompare,
    ManagerInternalApproval,
    InternalCandidacyConfidentialityLog,
    TalentMarketplaceUsageStat,
    InternalJobAlert,
    InternalGigAssignment,
)


# ──────────────────────────────────────────────────────────────────────────────
# SERIALIZERS
# ──────────────────────────────────────────────────────────────────────────────

class InternalRequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalRequisition
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InternalPostingWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalPostingWindow
        fields = "__all__"
        read_only_fields = ("id", "notification_sent_at", "created_at")


class InternalCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalCandidate
        fields = "__all__"
        read_only_fields = ("id", "manager_approval_at", "created_at", "updated_at")


class InternalTransferWorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalTransferWorkflow
        fields = "__all__"
        read_only_fields = (
            "id",
            "from_manager_approved_at",
            "to_manager_approved_at",
            "hr_approved_at",
            "created_at",
            "updated_at",
        )


class EmployeeSkillProfileBridgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSkillProfileBridge
        fields = "__all__"
        read_only_fields = ("id", "last_synced_from_hrm_at", "created_at", "updated_at")


class InternalReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalReferral
        fields = "__all__"
        read_only_fields = ("id", "bonus_paid_at", "created_at")


class RehireAlumniRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RehireAlumniRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class PipelineComparisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineComparison
        fields = "__all__"
        read_only_fields = ("id", "snapshotted_at")


class InternalCandidateCompareSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalCandidateCompare
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ManagerInternalApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerInternalApproval
        fields = "__all__"
        read_only_fields = ("id", "decided_at", "reminder_sent_at", "created_at")


class InternalCandidacyConfidentialityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalCandidacyConfidentialityLog
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class TalentMarketplaceUsageStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentMarketplaceUsageStat
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class InternalJobAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalJobAlert
        fields = "__all__"
        read_only_fields = ("id", "sent_at", "created_at")


class InternalGigAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalGigAssignment
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


# ──────────────────────────────────────────────────────────────────────────────
# VIEWSETS
# ──────────────────────────────────────────────────────────────────────────────

class InternalRequisitionViewSet(viewsets.ModelViewSet):
    serializer_class = InternalRequisitionSerializer

    def get_queryset(self):
        return InternalRequisition.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        """Open the internal requisition for applications."""
        req = self.get_object()
        req.status = "open"
        req.save(update_fields=["status"])
        return Response(InternalRequisitionSerializer(req).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close the internal requisition."""
        req = self.get_object()
        req.status = "closed"
        req.save(update_fields=["status"])
        return Response(InternalRequisitionSerializer(req).data)


class InternalPostingWindowViewSet(viewsets.ModelViewSet):
    serializer_class = InternalPostingWindowSerializer

    def get_queryset(self):
        return InternalPostingWindow.objects.filter(internal_req__tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def notify(self, request, pk=None):
        """Send notifications to eligible employees for this posting window."""
        window = self.get_object()
        window.notified_employees = True
        window.notification_sent_at = timezone.now()
        window.save(update_fields=["notified_employees", "notification_sent_at"])
        return Response(InternalPostingWindowSerializer(window).data)


class InternalCandidateViewSet(viewsets.ModelViewSet):
    serializer_class = InternalCandidateSerializer

    def get_queryset(self):
        return InternalCandidate.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def fast_track(self, request, pk=None):
        """Fast-track an internal candidate (e.g., alumni/rehire)."""
        candidate = self.get_object()
        candidate.fast_tracked = True
        candidate.save(update_fields=["fast_tracked"])
        return Response(InternalCandidateSerializer(candidate).data)

    @action(detail=True, methods=["post"])
    def convert_to_applicant(self, request, pk=None):
        """Link the internal candidate to an external application/candidate record."""
        candidate = self.get_object()
        candidate_id = request.data.get("candidate_id")
        application_id = request.data.get("application_id")
        if candidate_id:
            candidate.candidate_id = candidate_id
        if application_id:
            candidate.application_id = application_id
        candidate.save(update_fields=["candidate_id", "application_id"])
        return Response(InternalCandidateSerializer(candidate).data)


class InternalTransferWorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = InternalTransferWorkflowSerializer

    def get_queryset(self):
        return InternalTransferWorkflow.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def approve_from(self, request, pk=None):
        """Approve by the releasing (from) manager."""
        workflow = self.get_object()
        workflow.from_manager_approval = request.data.get("decision", "approved")
        workflow.from_manager_approved_at = timezone.now()
        workflow.save(update_fields=["from_manager_approval", "from_manager_approved_at"])
        return Response(InternalTransferWorkflowSerializer(workflow).data)

    @action(detail=True, methods=["post"])
    def approve_to(self, request, pk=None):
        """Approve by the receiving (to) manager."""
        workflow = self.get_object()
        workflow.to_manager_approval = request.data.get("decision", "approved")
        workflow.to_manager_approved_at = timezone.now()
        workflow.save(update_fields=["to_manager_approval", "to_manager_approved_at"])
        return Response(InternalTransferWorkflowSerializer(workflow).data)

    @action(detail=True, methods=["post"])
    def approve_hr(self, request, pk=None):
        """Approve by HR."""
        workflow = self.get_object()
        workflow.hr_approval = request.data.get("decision", "approved")
        workflow.hr_approved_at = timezone.now()
        workflow.save(update_fields=["hr_approval", "hr_approved_at"])
        return Response(InternalTransferWorkflowSerializer(workflow).data)


class EmployeeSkillProfileBridgeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSkillProfileBridgeSerializer

    def get_queryset(self):
        return EmployeeSkillProfileBridge.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def sync_from_hrm(self, request, pk=None):
        """Record that this profile was synced from the HRM system."""
        profile = self.get_object()
        if "skills" in request.data:
            profile.skills = request.data["skills"]
        if "certifications" in request.data:
            profile.certifications = request.data["certifications"]
        if "interests" in request.data:
            profile.interests = request.data["interests"]
        profile.last_synced_from_hrm_at = timezone.now()
        profile.save()
        return Response(EmployeeSkillProfileBridgeSerializer(profile).data)


class InternalReferralViewSet(viewsets.ModelViewSet):
    serializer_class = InternalReferralSerializer

    def get_queryset(self):
        return InternalReferral.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, referrer=self.request.user)


class RehireAlumniRecordViewSet(viewsets.ModelViewSet):
    serializer_class = RehireAlumniRecordSerializer

    def get_queryset(self):
        return RehireAlumniRecord.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def fast_track_approve(self, request, pk=None):
        """Fast-track approve a rehire or alumni record."""
        record = self.get_object()
        record.fast_track_approved = True
        record.save(update_fields=["fast_track_approved"])
        return Response(RehireAlumniRecordSerializer(record).data)


class PipelineComparisonViewSet(viewsets.ModelViewSet):
    serializer_class = PipelineComparisonSerializer

    def get_queryset(self):
        return PipelineComparison.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class InternalCandidateCompareViewSet(viewsets.ModelViewSet):
    serializer_class = InternalCandidateCompareSerializer

    def get_queryset(self):
        return InternalCandidateCompare.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)


class ManagerInternalApprovalViewSet(viewsets.ModelViewSet):
    serializer_class = ManagerInternalApprovalSerializer

    def get_queryset(self):
        return ManagerInternalApproval.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, manager=self.request.user)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        """Record the manager's approval decision for an internal applicant."""
        approval = self.get_object()
        approval.status = request.data.get("status", "approved")
        approval.decision_note = request.data.get("decision_note", "")
        approval.conditions = request.data.get("conditions", "")
        approval.decided_at = timezone.now()
        approval.save(update_fields=["status", "decision_note", "conditions", "decided_at"])
        return Response(ManagerInternalApprovalSerializer(approval).data)


class InternalCandidacyConfidentialityLogViewSet(viewsets.ModelViewSet):
    serializer_class = InternalCandidacyConfidentialityLogSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return InternalCandidacyConfidentialityLog.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, performed_by=self.request.user)


class TalentMarketplaceUsageStatViewSet(viewsets.ModelViewSet):
    serializer_class = TalentMarketplaceUsageStatSerializer

    def get_queryset(self):
        return TalentMarketplaceUsageStat.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class InternalJobAlertViewSet(viewsets.ModelViewSet):
    serializer_class = InternalJobAlertSerializer

    def get_queryset(self):
        return InternalJobAlert.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class InternalGigAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = InternalGigAssignmentSerializer

    def get_queryset(self):
        return InternalGigAssignment.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a gig assignment as completed."""
        assignment = self.get_object()
        assignment.status = "completed"
        assignment.outcome_notes = request.data.get("outcome_notes", assignment.outcome_notes)
        assignment.save(update_fields=["status", "outcome_notes"])
        return Response(InternalGigAssignmentSerializer(assignment).data)


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER & URL PATTERNS
# ──────────────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register(r"requisitions", InternalRequisitionViewSet, basename="bridge-req")
router.register(r"posting-windows", InternalPostingWindowViewSet, basename="bridge-posting-window")
router.register(r"candidates", InternalCandidateViewSet, basename="bridge-candidate")
router.register(r"transfer-workflows", InternalTransferWorkflowViewSet, basename="bridge-transfer")
router.register(r"skill-bridges", EmployeeSkillProfileBridgeViewSet, basename="bridge-skill-profile")
router.register(r"referrals", InternalReferralViewSet, basename="bridge-referral")
router.register(r"rehire-alumni", RehireAlumniRecordViewSet, basename="bridge-rehire-alumni")
router.register(r"pipeline-comparisons", PipelineComparisonViewSet, basename="bridge-pipeline-comparison")
router.register(r"candidate-compares", InternalCandidateCompareViewSet, basename="bridge-candidate-compare")
router.register(r"manager-approvals", ManagerInternalApprovalViewSet, basename="bridge-manager-approval")
router.register(r"confidentiality-logs", InternalCandidacyConfidentialityLogViewSet, basename="bridge-confidentiality-log")
router.register(r"marketplace-stats", TalentMarketplaceUsageStatViewSet, basename="bridge-marketplace-stat")
router.register(r"job-alerts", InternalJobAlertViewSet, basename="bridge-job-alert")
router.register(r"gig-assignments", InternalGigAssignmentViewSet, basename="bridge-gig-assignment")

urlpatterns = router.urls
