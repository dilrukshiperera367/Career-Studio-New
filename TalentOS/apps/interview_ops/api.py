"""
Interview Operations & Interviewer Enablement — Feature 7
API: ViewSets, Serializers, Custom Actions
Registered at: api/v1/interview-ops/
"""

from django.utils import timezone
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .models import (
    InterviewPlanTemplate, InterviewPlanStage,
    CompetencyQuestionBank, InterviewQuestion,
    InterviewKit, InterviewKitQuestion,
    InterviewerTrainingModule, InterviewerCertification,
    InterviewPrepBrief,
    PanelRoleAssignment,
    AvailabilitySlot,
    ConflictOfInterestDisclosure,
    NoteTakingTemplate, InterviewNote,
    FeedbackLock,
    DebriefWorkspace, DebriefVote,
    CalibrationAudit,
    ScorecardReminder,
    InterviewerWorkload,
    OnsiteAgenda, OnsiteAgendaSlot,
    TravelLogistics,
    InterviewerPerformanceRecord,
    NoShowPolicy,
    CandidateInterviewReminder,
    PanelDiversitySnapshot,
)


# ──────────────────────────────────────────────────────────────────────────────
# SERIALIZERS
# ──────────────────────────────────────────────────────────────────────────────

class InterviewPlanStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewPlanStage
        fields = "__all__"


class InterviewPlanTemplateSerializer(serializers.ModelSerializer):
    stages = InterviewPlanStageSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewPlanTemplate
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class CompetencyQuestionBankSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = CompetencyQuestionBank
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def get_question_count(self, obj):
        return obj.questions.count()


class InterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewQuestion
        fields = "__all__"
        read_only_fields = ("id", "usage_count", "created_at", "updated_at")


class InterviewKitQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewKitQuestion
        fields = "__all__"
        read_only_fields = ("id",)


class InterviewKitSerializer(serializers.ModelSerializer):
    kit_questions = InterviewKitQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewKit
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InterviewerTrainingModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerTrainingModule
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InterviewerCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerCertification
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InterviewPrepBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewPrepBrief
        fields = "__all__"
        read_only_fields = ("id", "sent_at", "viewed_at", "created_at", "updated_at")


class PanelRoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PanelRoleAssignment
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class ConflictOfInterestDisclosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConflictOfInterestDisclosure
        fields = "__all__"
        read_only_fields = ("id", "resolved_at", "created_at", "updated_at")


class NoteTakingTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteTakingTemplate
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InterviewNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewNote
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class FeedbackLockSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackLock
        fields = "__all__"
        read_only_fields = ("id", "unlocked_at", "created_at")


class DebriefVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebriefVote
        fields = "__all__"
        read_only_fields = ("id", "submitted_at", "created_at", "updated_at")


class DebriefWorkspaceSerializer(serializers.ModelSerializer):
    votes = DebriefVoteSerializer(many=True, read_only=True)

    class Meta:
        model = DebriefWorkspace
        fields = "__all__"
        read_only_fields = ("id", "decision_made_at", "created_at", "updated_at")


class CalibrationAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalibrationAudit
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class ScorecardReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScorecardReminder
        fields = "__all__"
        read_only_fields = ("id", "sent_at", "resolved_at")


class InterviewerWorkloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerWorkload
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class OnsiteAgendaSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnsiteAgendaSlot
        fields = "__all__"
        read_only_fields = ("id",)


class OnsiteAgendaSerializer(serializers.ModelSerializer):
    slots = OnsiteAgendaSlotSerializer(many=True, read_only=True)

    class Meta:
        model = OnsiteAgenda
        fields = "__all__"
        read_only_fields = ("id", "published_at", "created_at", "updated_at")


class TravelLogisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelLogistics
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class InterviewerPerformanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerPerformanceRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class NoShowPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = NoShowPolicy
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class CandidateInterviewReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateInterviewReminder
        fields = "__all__"
        read_only_fields = ("id", "sent_at")


class PanelDiversitySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PanelDiversitySnapshot
        fields = "__all__"
        read_only_fields = ("id", "checked_at")


# ──────────────────────────────────────────────────────────────────────────────
# VIEWSETS
# ──────────────────────────────────────────────────────────────────────────────

class InterviewPlanTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewPlanTemplateSerializer

    def get_queryset(self):
        return InterviewPlanTemplate.objects.filter(
            tenant=self.request.tenant_id
        ).prefetch_related("stages")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Clone a plan template and all its stages."""
        original = self.get_object()
        stages = list(original.stages.all())

        original.pk = None
        original.id = None
        original.name = f"{original.name} (Copy)"
        original.save()

        for stage in stages:
            stage.pk = None
            stage.id = None
            stage.plan = original
            stage.save()

        serializer = self.get_serializer(original)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InterviewPlanStageViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewPlanStageSerializer

    def get_queryset(self):
        qs = InterviewPlanStage.objects.select_related("plan")
        plan_id = self.request.query_params.get("plan")
        if plan_id:
            qs = qs.filter(plan__tenant=self.request.tenant_id, plan_id=plan_id)
        else:
            qs = qs.filter(plan__tenant=self.request.tenant_id)
        return qs


class CompetencyQuestionBankViewSet(viewsets.ModelViewSet):
    serializer_class = CompetencyQuestionBankSerializer

    def get_queryset(self):
        return CompetencyQuestionBank.objects.filter(
            tenant=self.request.tenant_id
        ).prefetch_related("questions")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)


class InterviewQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewQuestionSerializer

    def get_queryset(self):
        qs = InterviewQuestion.objects.select_related("bank")
        bank_id = self.request.query_params.get("bank")
        if bank_id:
            qs = qs.filter(bank__tenant=self.request.tenant_id, bank_id=bank_id)
        else:
            qs = qs.filter(bank__tenant=self.request.tenant_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InterviewKitViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewKitSerializer

    def get_queryset(self):
        return InterviewKit.objects.filter(
            tenant=self.request.tenant_id
        ).prefetch_related("kit_questions")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Mark the kit as published."""
        kit = self.get_object()
        kit.is_published = True
        kit.save(update_fields=["is_published"])
        return Response({"status": "published"})


class InterviewKitQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewKitQuestionSerializer

    def get_queryset(self):
        qs = InterviewKitQuestion.objects.select_related("kit", "question")
        kit_id = self.request.query_params.get("kit")
        if kit_id:
            qs = qs.filter(kit__tenant=self.request.tenant_id, kit_id=kit_id)
        else:
            qs = qs.filter(kit__tenant=self.request.tenant_id)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        # Increment usage_count on the linked question
        if instance.question_id:
            InterviewQuestion.objects.filter(pk=instance.question_id).update(
                usage_count=instance.question.usage_count + 1
            )


class InterviewerTrainingModuleViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewerTrainingModuleSerializer

    def get_queryset(self):
        return InterviewerTrainingModule.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class InterviewerCertificationViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewerCertificationSerializer

    def get_queryset(self):
        return InterviewerCertification.objects.filter(
            tenant=self.request.tenant_id
        ).select_related("module", "interviewer")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a certification as passed or failed and compute expiry."""
        cert = self.get_object()
        result = request.data.get("result")  # "passed" or "failed"
        score = request.data.get("score")

        if result not in ("passed", "failed"):
            return Response(
                {"detail": "result must be 'passed' or 'failed'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cert.status = result
        cert.completed_at = timezone.now()
        if score is not None:
            cert.score = int(score)

        # Compute expiry
        months = cert.module.recertification_months
        if result == "passed" and months > 0:
            from dateutil.relativedelta import relativedelta
            cert.expires_at = (timezone.now() + relativedelta(months=months)).date()

        cert.save()
        return Response(InterviewerCertificationSerializer(cert).data)


class InterviewPrepBriefViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewPrepBriefSerializer

    def get_queryset(self):
        return InterviewPrepBrief.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Mark the prep brief as sent."""
        brief = self.get_object()
        brief.is_sent = True
        brief.sent_at = timezone.now()
        brief.save(update_fields=["is_sent", "sent_at"])
        return Response({"status": "sent", "sent_at": brief.sent_at})

    @action(detail=True, methods=["post"])
    def mark_viewed(self, request, pk=None):
        """Record that the interviewer viewed the brief."""
        brief = self.get_object()
        if not brief.viewed_at:
            brief.viewed_at = timezone.now()
            brief.save(update_fields=["viewed_at"])
        return Response({"status": "viewed", "viewed_at": brief.viewed_at})


class PanelRoleAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = PanelRoleAssignmentSerializer

    def get_queryset(self):
        return PanelRoleAssignment.objects.filter(
            tenant=self.request.tenant_id
        ).select_related("interviewer")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class AvailabilitySlotViewSet(viewsets.ModelViewSet):
    serializer_class = AvailabilitySlotSerializer

    def get_queryset(self):
        qs = AvailabilitySlot.objects.filter(tenant=self.request.tenant_id)
        interviewer_id = self.request.query_params.get("interviewer")
        if interviewer_id:
            qs = qs.filter(interviewer_id=interviewer_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class ConflictOfInterestDisclosureViewSet(viewsets.ModelViewSet):
    serializer_class = ConflictOfInterestDisclosureSerializer

    def get_queryset(self):
        return ConflictOfInterestDisclosure.objects.filter(
            tenant=self.request.tenant_id
        ).select_related("interviewer", "resolved_by")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve a COI disclosure (cleared / recused / waived)."""
        disclosure = self.get_object()
        resolution = request.data.get("resolution")
        valid = ("cleared", "recused", "waived")

        if resolution not in valid:
            return Response(
                {"detail": f"resolution must be one of {valid}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        disclosure.resolution = resolution
        disclosure.resolved_by = request.user
        disclosure.resolved_at = timezone.now()
        disclosure.save(update_fields=["resolution", "resolved_by", "resolved_at"])
        return Response(ConflictOfInterestDisclosureSerializer(disclosure).data)


class NoteTakingTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = NoteTakingTemplateSerializer

    def get_queryset(self):
        return NoteTakingTemplate.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, created_by=self.request.user)


class InterviewNoteViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewNoteSerializer

    def get_queryset(self):
        return InterviewNote.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class FeedbackLockViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackLockSerializer

    def get_queryset(self):
        return FeedbackLock.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        """Admin override to unlock an interviewer's feedback view."""
        lock = self.get_object()
        lock.status = "unlocked_by_admin"
        lock.unlocked_at = timezone.now()
        lock.unlocked_by = request.user
        lock.save(update_fields=["status", "unlocked_at", "unlocked_by"])
        return Response(FeedbackLockSerializer(lock).data)


class DebriefWorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = DebriefWorkspaceSerializer

    def get_queryset(self):
        return DebriefWorkspace.objects.filter(
            tenant=self.request.tenant_id
        ).prefetch_related("votes")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def submit_vote(self, request, pk=None):
        """Submit (or update) the current user's debrief vote."""
        workspace = self.get_object()
        vote_value = request.data.get("vote")
        if not vote_value:
            return Response({"detail": "vote is required"}, status=status.HTTP_400_BAD_REQUEST)

        vote, _ = DebriefVote.objects.get_or_create(
            workspace=workspace, voter=request.user
        )
        vote.vote = vote_value
        vote.rationale = request.data.get("rationale", vote.rationale)
        vote.top_strength = request.data.get("top_strength", vote.top_strength)
        vote.top_concern = request.data.get("top_concern", vote.top_concern)
        vote.is_submitted = True
        vote.submitted_at = timezone.now()
        vote.save()
        return Response(DebriefVoteSerializer(vote).data)

    @action(detail=True, methods=["post"])
    def reveal_votes(self, request, pk=None):
        """Reveal all submitted votes (called once all have submitted)."""
        workspace = self.get_object()
        votes = workspace.votes.filter(is_submitted=True)
        return Response(DebriefVoteSerializer(votes, many=True).data)

    @action(detail=True, methods=["post"])
    def finalize_decision(self, request, pk=None):
        """Set the final hiring decision."""
        workspace = self.get_object()
        decision = request.data.get("final_decision")
        if not decision:
            return Response({"detail": "final_decision is required"}, status=status.HTTP_400_BAD_REQUEST)

        workspace.final_decision = decision
        workspace.decision_rationale = request.data.get("decision_rationale", "")
        workspace.decision_made_at = timezone.now()
        workspace.decision_made_by = request.user
        workspace.save(update_fields=[
            "final_decision", "decision_rationale",
            "decision_made_at", "decision_made_by",
        ])
        return Response(DebriefWorkspaceSerializer(workspace).data)


class DebriefVoteViewSet(viewsets.ModelViewSet):
    serializer_class = DebriefVoteSerializer

    def get_queryset(self):
        return DebriefVote.objects.filter(
            workspace__tenant=self.request.tenant_id
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Finalise a vote (lock it in)."""
        vote = self.get_object()
        vote.is_submitted = True
        vote.submitted_at = timezone.now()
        vote.save(update_fields=["is_submitted", "submitted_at"])
        return Response(DebriefVoteSerializer(vote).data)


class CalibrationAuditViewSet(viewsets.ModelViewSet):
    serializer_class = CalibrationAuditSerializer

    def get_queryset(self):
        return CalibrationAudit.objects.filter(
            tenant=self.request.tenant_id
        ).select_related("interviewer", "job")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class ScorecardReminderViewSet(viewsets.ModelViewSet):
    serializer_class = ScorecardReminderSerializer

    def get_queryset(self):
        return ScorecardReminder.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark the reminder as resolved (scorecard submitted)."""
        reminder = self.get_object()
        reminder.resolved = True
        reminder.resolved_at = timezone.now()
        reminder.save(update_fields=["resolved", "resolved_at"])
        return Response(ScorecardReminderSerializer(reminder).data)


class InterviewerWorkloadViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewerWorkloadSerializer

    def get_queryset(self):
        return InterviewerWorkload.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def check_overload(self, request, pk=None):
        """Re-compute the is_overloaded flag based on current counts."""
        workload = self.get_object()
        workload.is_overloaded = (
            workload.scheduled_count > workload.max_interviews_per_week
            or workload.scheduled_hours > workload.max_hours_per_week
        )
        workload.save(update_fields=["is_overloaded"])
        return Response(InterviewerWorkloadSerializer(workload).data)


class OnsiteAgendaViewSet(viewsets.ModelViewSet):
    serializer_class = OnsiteAgendaSerializer

    def get_queryset(self):
        return OnsiteAgenda.objects.filter(
            tenant=self.request.tenant_id
        ).prefetch_related("slots")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def publish_to_candidate(self, request, pk=None):
        """Mark agenda as published and visible to the candidate."""
        agenda = self.get_object()
        agenda.is_published_to_candidate = True
        agenda.published_at = timezone.now()
        agenda.save(update_fields=["is_published_to_candidate", "published_at"])
        return Response(OnsiteAgendaSerializer(agenda).data)


class OnsiteAgendaSlotViewSet(viewsets.ModelViewSet):
    serializer_class = OnsiteAgendaSlotSerializer

    def get_queryset(self):
        qs = OnsiteAgendaSlot.objects.select_related("agenda", "host")
        agenda_id = self.request.query_params.get("agenda")
        if agenda_id:
            qs = qs.filter(agenda__tenant=self.request.tenant_id, agenda_id=agenda_id)
        else:
            qs = qs.filter(agenda__tenant=self.request.tenant_id)
        return qs


class TravelLogisticsViewSet(viewsets.ModelViewSet):
    serializer_class = TravelLogisticsSerializer

    def get_queryset(self):
        return TravelLogistics.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class InterviewerPerformanceRecordViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewerPerformanceRecordSerializer

    def get_queryset(self):
        qs = InterviewerPerformanceRecord.objects.filter(tenant=self.request.tenant_id)
        interviewer_id = self.request.query_params.get("interviewer")
        if interviewer_id:
            qs = qs.filter(interviewer_id=interviewer_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class NoShowPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = NoShowPolicySerializer

    def get_queryset(self):
        return NoShowPolicy.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class CandidateInterviewReminderViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateInterviewReminderSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return CandidateInterviewReminder.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id)


class PanelDiversitySnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = PanelDiversitySnapshotSerializer

    def get_queryset(self):
        return PanelDiversitySnapshot.objects.filter(tenant=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant_id, checked_by=self.request.user)

    @action(detail=True, methods=["post"])
    def run_check(self, request, pk=None):
        """
        Evaluate the panel against the tenant's diversity policy.
        Expects: {"gender_diversity_met": bool, "ethnic_diversity_met": bool,
                  "diversity_policy_name": str}
        """
        snapshot = self.get_object()
        snapshot.gender_diversity_met = request.data.get(
            "gender_diversity_met", snapshot.gender_diversity_met
        )
        snapshot.ethnic_diversity_met = request.data.get(
            "ethnic_diversity_met", snapshot.ethnic_diversity_met
        )
        snapshot.diversity_policy_name = request.data.get(
            "diversity_policy_name", snapshot.diversity_policy_name
        )
        # Overall flag: both criteria must be met (or null = not applicable)
        gender_ok = snapshot.gender_diversity_met in (True, None)
        ethnic_ok = snapshot.ethnic_diversity_met in (True, None)
        snapshot.diversity_policy_met = gender_ok and ethnic_ok
        snapshot.checked_by = request.user
        snapshot.save()
        return Response(PanelDiversitySnapshotSerializer(snapshot).data)


# ──────────────────────────────────────────────────────────────────────────────
# ROUTER & URL PATTERNS
# ──────────────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register(r"plan-templates", InterviewPlanTemplateViewSet, basename="plan-template")
router.register(r"plan-stages", InterviewPlanStageViewSet, basename="plan-stage")
router.register(r"question-banks", CompetencyQuestionBankViewSet, basename="question-bank")
router.register(r"questions", InterviewQuestionViewSet, basename="interview-question")
router.register(r"kits", InterviewKitViewSet, basename="interview-kit")
router.register(r"kit-questions", InterviewKitQuestionViewSet, basename="kit-question")
router.register(r"training-modules", InterviewerTrainingModuleViewSet, basename="training-module")
router.register(r"certifications", InterviewerCertificationViewSet, basename="certification")
router.register(r"prep-briefs", InterviewPrepBriefViewSet, basename="prep-brief")
router.register(r"panel-roles", PanelRoleAssignmentViewSet, basename="panel-role")
router.register(r"availability", AvailabilitySlotViewSet, basename="availability-slot")
router.register(r"coi", ConflictOfInterestDisclosureViewSet, basename="coi")
router.register(r"note-templates", NoteTakingTemplateViewSet, basename="note-template")
router.register(r"notes", InterviewNoteViewSet, basename="interview-note")
router.register(r"feedback-locks", FeedbackLockViewSet, basename="feedback-lock")
router.register(r"debrief-workspaces", DebriefWorkspaceViewSet, basename="debrief-workspace")
router.register(r"debrief-votes", DebriefVoteViewSet, basename="debrief-vote")
router.register(r"calibration-audits", CalibrationAuditViewSet, basename="calibration-audit")
router.register(r"scorecard-reminders", ScorecardReminderViewSet, basename="scorecard-reminder")
router.register(r"workloads", InterviewerWorkloadViewSet, basename="interviewer-workload")
router.register(r"onsite-agendas", OnsiteAgendaViewSet, basename="onsite-agenda")
router.register(r"onsite-slots", OnsiteAgendaSlotViewSet, basename="onsite-slot")
router.register(r"travel-logistics", TravelLogisticsViewSet, basename="travel-logistics")
router.register(r"performance-records", InterviewerPerformanceRecordViewSet, basename="performance-record")
router.register(r"no-show-policies", NoShowPolicyViewSet, basename="no-show-policy")
router.register(r"candidate-reminders", CandidateInterviewReminderViewSet, basename="candidate-reminder")
router.register(r"panel-diversity", PanelDiversitySnapshotViewSet, basename="panel-diversity")

urlpatterns = router.urls
