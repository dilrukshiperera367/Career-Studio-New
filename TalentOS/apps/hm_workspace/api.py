"""
Hiring Manager Workspace — Feature 8
API: ViewSets, Serializers, Custom Actions
Registered at: api/v1/hm/
"""

from django.utils import timezone
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .models import (
    RoleIntakeForm,
    ShortlistReview,
    CandidateComparison,
    HMFeedbackInboxItem,
    HMApprovalTask,
    HMDecisionQueueItem,
    ReqHealthSnapshot,
    TimeToFillRisk,
    CandidateMessageApproval,
    HMSLAReminder,
    HMCalibrationView,
    HMOfferApproval,
    RecruiterManagerNote,
    ManagerTrainingPrompt,
    HMDashboardStat,
)


# ──────────────────────────────────────────────────────────────────────────────
# SERIALIZERS
# ──────────────────────────────────────────────────────────────────────────────

class RoleIntakeFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleIntakeForm
        fields = "__all__"
        read_only_fields = ("id", "submitted_at", "approved_at", "approved_by", "created_at", "updated_at")


class ShortlistReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortlistReview
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class CandidateComparisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateComparison
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class HMFeedbackInboxItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = HMFeedbackInboxItem
        fields = "__all__"
        read_only_fields = ("id", "read_at", "created_at")


class HMApprovalTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = HMApprovalTask
        fields = "__all__"
        read_only_fields = ("id", "completed_at", "created_at", "updated_at")


class HMDecisionQueueItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = HMDecisionQueueItem
        fields = "__all__"
        read_only_fields = ("id", "resolved_at", "created_at")


class ReqHealthSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReqHealthSnapshot
        fields = "__all__"
        read_only_fields = ("id", "snapshotted_at")


class TimeToFillRiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeToFillRisk
        fields = "__all__"
        read_only_fields = ("id", "assessed_at")


class CandidateMessageApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateMessageApproval
        fields = "__all__"
        read_only_fields = ("id", "approved_at", "sent_at", "created_at")


class HMSLAReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = HMSLAReminder
        fields = "__all__"
        read_only_fields = ("id", "sent_at", "resolved_at", "escalated_at", "created_at")


class HMCalibrationViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HMCalibrationView
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class HMOfferApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HMOfferApproval
        fields = "__all__"
        read_only_fields = ("id", "decided_at", "created_at", "updated_at")


class RecruiterManagerNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterManagerNote
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ManagerTrainingPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerTrainingPrompt
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class HMDashboardStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = HMDashboardStat
        fields = "__all__"
        read_only_fields = ("id", "computed_at")


# ──────────────────────────────────────────────────────────────────────────────
# VIEWSETS
# ──────────────────────────────────────────────────────────────────────────────

class RoleIntakeFormViewSet(viewsets.ModelViewSet):
    serializer_class = RoleIntakeFormSerializer

    def get_queryset(self):
        return RoleIntakeForm.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit the intake form for review."""
        form = self.get_object()
        form.status = "submitted"
        form.submitted_at = timezone.now()
        form.save(update_fields=["status", "submitted_at"])
        return Response(RoleIntakeFormSerializer(form).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve the intake form."""
        form = self.get_object()
        form.status = "approved"
        form.approved_at = timezone.now()
        form.approved_by = request.user
        form.save(update_fields=["status", "approved_at", "approved_by"])
        return Response(RoleIntakeFormSerializer(form).data)


class ShortlistReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ShortlistReviewSerializer

    def get_queryset(self):
        return ShortlistReview.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class CandidateComparisonViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateComparisonSerializer

    def get_queryset(self):
        return CandidateComparison.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)


class HMFeedbackInboxItemViewSet(viewsets.ModelViewSet):
    serializer_class = HMFeedbackInboxItemSerializer

    def get_queryset(self):
        return HMFeedbackInboxItem.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark a feedback inbox item as read."""
        item = self.get_object()
        if not item.is_read:
            item.is_read = True
            item.read_at = timezone.now()
            item.save(update_fields=["is_read", "read_at"])
        return Response(HMFeedbackInboxItemSerializer(item).data)


class HMApprovalTaskViewSet(viewsets.ModelViewSet):
    serializer_class = HMApprovalTaskSerializer

    def get_queryset(self):
        return HMApprovalTask.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete an approval task with a decision."""
        task = self.get_object()
        new_status = request.data.get("status", "approved")
        decision_note = request.data.get("decision_note", "")
        task.status = new_status
        task.completed_at = timezone.now()
        task.decision_note = decision_note
        task.save(update_fields=["status", "completed_at", "decision_note"])
        return Response(HMApprovalTaskSerializer(task).data)


class HMDecisionQueueItemViewSet(viewsets.ModelViewSet):
    serializer_class = HMDecisionQueueItemSerializer

    def get_queryset(self):
        return HMDecisionQueueItem.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve a decision queue item."""
        item = self.get_object()
        decision = request.data.get("decision", "")
        decision_note = request.data.get("decision_note", "")
        item.decision = decision
        item.decision_note = decision_note
        item.is_resolved = True
        item.resolved_at = timezone.now()
        item.save(update_fields=["decision", "decision_note", "is_resolved", "resolved_at"])
        return Response(HMDecisionQueueItemSerializer(item).data)


class ReqHealthSnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = ReqHealthSnapshotSerializer

    def get_queryset(self):
        return ReqHealthSnapshot.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=False, methods=["post"])
    def compute(self, request):
        """Compute and save a new req health snapshot."""
        job_id = request.data.get("job_id")
        if not job_id:
            return Response({"detail": "job_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        snapshot = ReqHealthSnapshot.objects.create(
            tenant=self.request.tenant_id,
            job_id=job_id,
            pipeline_total=request.data.get("pipeline_total", 0),
            pipeline_by_stage=request.data.get("pipeline_by_stage", {}),
            days_open=request.data.get("days_open", 0),
            target_days=request.data.get("target_days", 45),
            interviews_scheduled=request.data.get("interviews_scheduled", 0),
            offers_extended=request.data.get("offers_extended", 0),
            offers_accepted=request.data.get("offers_accepted", 0),
            drop_rate=request.data.get("drop_rate", 0),
            health_score=request.data.get("health_score", 0),
            health_flags=request.data.get("health_flags", []),
        )
        return Response(ReqHealthSnapshotSerializer(snapshot).data, status=status.HTTP_201_CREATED)


class TimeToFillRiskViewSet(viewsets.ModelViewSet):
    serializer_class = TimeToFillRiskSerializer

    def get_queryset(self):
        return TimeToFillRisk.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class CandidateMessageApprovalViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateMessageApprovalSerializer

    def get_queryset(self):
        return CandidateMessageApproval.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a candidate message."""
        msg = self.get_object()
        msg.status = "approved"
        msg.approver = request.user
        msg.approved_at = timezone.now()
        msg.reviewer_note = request.data.get("reviewer_note", "")
        msg.save(update_fields=["status", "approver", "approved_at", "reviewer_note"])
        return Response(CandidateMessageApprovalSerializer(msg).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a candidate message."""
        msg = self.get_object()
        msg.status = "rejected"
        msg.approver = request.user
        msg.reviewer_note = request.data.get("reviewer_note", "")
        msg.save(update_fields=["status", "approver", "reviewer_note"])
        return Response(CandidateMessageApprovalSerializer(msg).data)


class HMSLAReminderViewSet(viewsets.ModelViewSet):
    serializer_class = HMSLAReminderSerializer

    def get_queryset(self):
        return HMSLAReminder.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        """Escalate an overdue SLA reminder."""
        reminder = self.get_object()
        reminder.escalated = True
        reminder.escalated_at = timezone.now()
        reminder.save(update_fields=["escalated", "escalated_at"])
        return Response(HMSLAReminderSerializer(reminder).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark the SLA reminder as resolved."""
        reminder = self.get_object()
        reminder.is_resolved = True
        reminder.resolved_at = timezone.now()
        reminder.save(update_fields=["is_resolved", "resolved_at"])
        return Response(HMSLAReminderSerializer(reminder).data)


class HMCalibrationViewViewSet(viewsets.ModelViewSet):
    serializer_class = HMCalibrationViewSerializer

    def get_queryset(self):
        return HMCalibrationView.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class HMOfferApprovalViewSet(viewsets.ModelViewSet):
    serializer_class = HMOfferApprovalSerializer

    def get_queryset(self):
        return HMOfferApproval.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        """Approve or reject a pending offer."""
        approval = self.get_object()
        new_status = request.data.get("status", "approved")
        decision_note = request.data.get("decision_note", "")
        approval.status = new_status
        approval.decision_note = decision_note
        approval.decided_at = timezone.now()
        approval.hiring_manager = request.user
        approval.save(update_fields=["status", "decision_note", "decided_at", "hiring_manager"])
        return Response(HMOfferApprovalSerializer(approval).data)


class RecruiterManagerNoteViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterManagerNoteSerializer

    def get_queryset(self):
        return RecruiterManagerNote.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, author=self.request.user)


class ManagerTrainingPromptViewSet(viewsets.ModelViewSet):
    serializer_class = ManagerTrainingPromptSerializer

    def get_queryset(self):
        return ManagerTrainingPrompt.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class HMDashboardStatViewSet(viewsets.ModelViewSet):
    serializer_class = HMDashboardStatSerializer

    def get_queryset(self):
        return HMDashboardStat.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        """Recompute (or create) dashboard stats for the requesting user."""
        stat, _ = HMDashboardStat.objects.get_or_create(
            tenant=self.request.tenant_id,
            hiring_manager=request.user,
        )
        # Accept caller-supplied counts or keep existing values
        stat.open_reqs = request.data.get("open_reqs", stat.open_reqs)
        stat.pending_approvals = request.data.get("pending_approvals", stat.pending_approvals)
        stat.pending_feedback = request.data.get("pending_feedback", stat.pending_feedback)
        stat.pending_decisions = request.data.get("pending_decisions", stat.pending_decisions)
        stat.overdue_slas = request.data.get("overdue_slas", stat.overdue_slas)
        stat.active_offers = request.data.get("active_offers", stat.active_offers)
        stat.avg_ttf_days = request.data.get("avg_ttf_days", stat.avg_ttf_days)
        stat.reqs_at_risk = request.data.get("reqs_at_risk", stat.reqs_at_risk)
        stat.save()
        return Response(HMDashboardStatSerializer(stat).data)


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER & URL PATTERNS
# ──────────────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register(r"intake-forms", RoleIntakeFormViewSet, basename="hm-intake-form")
router.register(r"shortlist-reviews", ShortlistReviewViewSet, basename="hm-shortlist-review")
router.register(r"comparisons", CandidateComparisonViewSet, basename="hm-comparison")
router.register(r"feedback-inbox", HMFeedbackInboxItemViewSet, basename="hm-feedback-inbox")
router.register(r"approval-tasks", HMApprovalTaskViewSet, basename="hm-approval-task")
router.register(r"decision-queue", HMDecisionQueueItemViewSet, basename="hm-decision-queue")
router.register(r"req-health", ReqHealthSnapshotViewSet, basename="hm-req-health")
router.register(r"ttf-risks", TimeToFillRiskViewSet, basename="hm-ttf-risk")
router.register(r"message-approvals", CandidateMessageApprovalViewSet, basename="hm-message-approval")
router.register(r"sla-reminders", HMSLAReminderViewSet, basename="hm-sla-reminder")
router.register(r"calibration", HMCalibrationViewViewSet, basename="hm-calibration")
router.register(r"offer-approvals", HMOfferApprovalViewSet, basename="hm-offer-approval")
router.register(r"collab-notes", RecruiterManagerNoteViewSet, basename="hm-collab-note")
router.register(r"training-prompts", ManagerTrainingPromptViewSet, basename="hm-training-prompt")
router.register(r"dashboard-stats", HMDashboardStatViewSet, basename="hm-dashboard-stat")

urlpatterns = router.urls
