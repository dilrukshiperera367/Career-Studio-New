"""API for Assessments & Screening Orchestration — Feature 6.

Covers all ViewSets for:
- Pre-screen questionnaires + knockout questions
- Weighted screening rules engine
- Credential/license verification
- Assessment catalog (all types) + vendor ordering
- Normalized results + anti-cheating
- Alternate paths for accommodations + waivers
- Screen decision taxonomy + structured disqualification
- Screen-review queues + blind review mode
- Audit trail for screening decisions
- Explainable match & screening logic
- Candidate appeal / reconsideration
"""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from django.utils import timezone
from rest_framework.routers import DefaultRouter

from apps.assessments.models import (
    AssessmentVendor, AssessmentCatalogItem, AssessmentOrder,
    AssessmentResult, AssessmentWaiver, AlternateAssessmentPath,
    ScreeningQuestionnaire, ScreeningQuestion, ScreeningQuestionnaireResponse,
    ScreeningRuleSet, ScreeningRule, ScreeningRuleEvaluation,
    CredentialVerification, ScreeningDecisionReason, ScreeningDecision,
    ScreenReviewQueue, ScreeningAuditEntry, ScreeningAppeal,
    ExplainableMatchSnapshot,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess


# ── Serializers ───────────────────────────────────────────────────────────────

class AssessmentVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentVendor
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AssessmentCatalogItemSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = AssessmentCatalogItem
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AssessmentOrderSerializer(serializers.ModelSerializer):
    catalog_item_name = serializers.CharField(source="catalog_item.name", read_only=True)

    class Meta:
        model = AssessmentOrder
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "ordered_by"]


class AssessmentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentResult
        fields = "__all__"
        read_only_fields = ["id", "received_at", "updated_at"]


class AssessmentWaiverSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentWaiver
        fields = "__all__"
        read_only_fields = ["id", "created_at", "waived_by"]


class AlternateAssessmentPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlternateAssessmentPath
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ScreeningQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningQuestion
        fields = "__all__"


class ScreeningQuestionnaireSerializer(serializers.ModelSerializer):
    questions = ScreeningQuestionSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = ScreeningQuestionnaire
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class ScreeningQuestionnaireResponseSerializer(serializers.ModelSerializer):
    questionnaire_title = serializers.CharField(source="questionnaire.title", read_only=True)

    class Meta:
        model = ScreeningQuestionnaireResponse
        fields = "__all__"
        read_only_fields = ["id", "submitted_at", "updated_at", "computed_score",
                            "knockout_triggered", "knockout_question"]


class ScreeningRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningRule
        fields = "__all__"


class ScreeningRuleSetSerializer(serializers.ModelSerializer):
    rules = ScreeningRuleSerializer(many=True, read_only=True)
    rule_count = serializers.IntegerField(source="rules.count", read_only=True)

    class Meta:
        model = ScreeningRuleSet
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class ScreeningRuleEvaluationSerializer(serializers.ModelSerializer):
    rule_set_name = serializers.CharField(source="rule_set.name", read_only=True)

    class Meta:
        model = ScreeningRuleEvaluation
        fields = "__all__"
        read_only_fields = ["id", "evaluated_at"]


class CredentialVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CredentialVerification
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ScreeningDecisionReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningDecisionReason
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ScreeningDecisionSerializer(serializers.ModelSerializer):
    reason_label = serializers.CharField(source="reason.label", read_only=True)
    reason_category = serializers.CharField(source="reason.category", read_only=True)

    class Meta:
        model = ScreeningDecision
        fields = "__all__"
        read_only_fields = ["id", "decided_at", "updated_at", "decided_by"]


class ScreenReviewQueueSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return None

    class Meta:
        model = ScreenReviewQueue
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ScreeningAuditEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningAuditEntry
        fields = "__all__"
        read_only_fields = ["id", "occurred_at"]


class ScreeningAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningAppeal
        fields = "__all__"
        read_only_fields = ["id", "submitted_at", "updated_at"]


class ExplainableMatchSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExplainableMatchSnapshot
        fields = "__all__"
        read_only_fields = ["id", "generated_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class AssessmentVendorViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentVendorSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]

    def get_queryset(self):
        return AssessmentVendor.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class AssessmentCatalogItemViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentCatalogItemSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["assessment_type", "is_active", "requires_human_review",
                        "eu_ai_act_risk_level", "anti_cheating_enabled"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return AssessmentCatalogItem.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("vendor")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class AssessmentOrderViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentOrderSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "anti_cheating_cleared"]
    ordering_fields = ["created_at", "expires_at"]

    def get_queryset(self):
        return AssessmentOrder.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("catalog_item", "application")

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            ordered_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a pending or invited assessment order."""
        order = self.get_object()
        if order.status in ("completed", "cancelled"):
            return Response(
                {"error": f"Cannot cancel order in status '{order.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        return Response(AssessmentOrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="clear-anti-cheat")
    def clear_anti_cheat(self, request, pk=None):
        """Human reviewer clears anti-cheating flags."""
        order = self.get_object()
        order.anti_cheating_cleared = True
        order.save(update_fields=["anti_cheating_cleared", "updated_at"])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=order.application,
            action="anti_cheat_cleared",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            payload={"order_id": str(order.id)},
        )
        return Response(AssessmentOrderSerializer(order).data)


class AssessmentResultViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentResultSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["passed", "human_reviewed"]

    def get_queryset(self):
        return AssessmentResult.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("order")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def human_review(self, request, pk=None):
        """Record human review of an AI-generated assessment result (EU AI Act)."""
        result = self.get_object()
        result.human_reviewed = True
        result.human_reviewer = request.user
        result.human_review_note = request.data.get("note", "")
        override = request.data.get("override")
        if override is not None:
            result.human_override = bool(override)
        result.save(update_fields=[
            "human_reviewed", "human_reviewer", "human_review_note",
            "human_override", "updated_at",
        ])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=result.order.application,
            action="anti_cheat_cleared",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            is_system_action=False,
            payload={"result_id": str(result.id), "override": override},
        )
        return Response(AssessmentResultSerializer(result).data)


class AssessmentWaiverViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentWaiverSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["reason"]

    def get_queryset(self):
        return AssessmentWaiver.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        waiver = serializer.save(
            tenant_id=self.request.tenant_id,
            waived_by=self.request.user,
        )
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=waiver.application,
            action="waiver_granted",
            actor=self.request.user,
            actor_label=f"{self.request.user.first_name} {self.request.user.last_name}",
            payload={"reason": waiver.reason, "catalog_item": str(waiver.catalog_item_id)},
        )


class AlternateAssessmentPathViewSet(viewsets.ModelViewSet):
    serializer_class = AlternateAssessmentPathSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        return AlternateAssessmentPath.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class ScreeningQuestionnaireViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningQuestionnaireSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active", "blind_review_enforced"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        return ScreeningQuestionnaire.objects.filter(
            tenant_id=self.request.tenant_id
        ).prefetch_related("questions")

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        """Clone a questionnaire and all its questions."""
        original = self.get_object()
        new_q = ScreeningQuestionnaire.objects.create(
            tenant_id=self.request.tenant_id,
            title=f"{original.title} (Copy)",
            description=original.description,
            is_active=False,
            blind_review_enforced=original.blind_review_enforced,
            created_by=request.user,
        )
        for q in original.questions.all():
            ScreeningQuestion.objects.create(
                questionnaire=new_q,
                order=q.order,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                is_required=q.is_required,
                is_knockout=q.is_knockout,
                knockout_disqualifying_values=q.knockout_disqualifying_values,
                knockout_reason_code=q.knockout_reason_code,
                weight=q.weight,
                ideal_answer=q.ideal_answer,
                scoring_rubric=q.scoring_rubric,
                help_text_for_candidate=q.help_text_for_candidate,
            )
        return Response(ScreeningQuestionnaireSerializer(new_q).data, status=status.HTTP_201_CREATED)


class ScreeningQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningQuestionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["question_type", "is_required", "is_knockout"]

    def get_queryset(self):
        qs = ScreeningQuestion.objects.filter(
            questionnaire__tenant_id=self.request.tenant_id
        )
        questionnaire_id = self.request.query_params.get("questionnaire")
        if questionnaire_id:
            qs = qs.filter(questionnaire_id=questionnaire_id)
        return qs.order_by("order")


class ScreeningQuestionnaireResponseViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningQuestionnaireResponseSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["knockout_triggered"]

    def get_queryset(self):
        return ScreeningQuestionnaireResponse.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("questionnaire", "application")

    def perform_create(self, serializer):
        """Save response and compute weighted score + knockout check."""
        questionnaire = serializer.validated_data["questionnaire"]
        answers = serializer.validated_data.get("answers", {})
        questions = questionnaire.questions.all()

        total_score = 0.0
        knockout_triggered = False
        knockout_question = None

        for question in questions:
            answer = answers.get(str(question.id))
            if answer is None:
                continue

            # Knockout check
            if question.is_knockout and question.knockout_disqualifying_values:
                answer_str = str(answer) if not isinstance(answer, list) else answer
                disq = question.knockout_disqualifying_values
                if isinstance(answer_str, list):
                    if any(v in disq for v in answer_str):
                        knockout_triggered = True
                        knockout_question = question
                elif answer_str in disq:
                    knockout_triggered = True
                    knockout_question = question

            # Scoring
            if question.weight > 0:
                rubric = question.scoring_rubric or {}
                ideal = question.ideal_answer
                answer_key = str(answer) if not isinstance(answer, list) else ",".join(str(a) for a in answer)
                if ideal is not None and answer == ideal:
                    total_score += question.weight
                elif answer_key in rubric:
                    total_score += rubric[answer_key]

        instance = serializer.save(
            tenant_id=self.request.tenant_id,
            computed_score=round(total_score, 2),
            knockout_triggered=knockout_triggered,
            knockout_question=knockout_question,
        )
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=instance.application,
            action="questionnaire_submitted",
            is_system_action=True,
            payload={
                "questionnaire_id": str(questionnaire.id),
                "score": total_score,
                "knockout": knockout_triggered,
            },
        )
        if knockout_triggered:
            ScreeningAuditEntry.objects.create(
                tenant_id=self.request.tenant_id,
                application=instance.application,
                action="knockout_triggered",
                is_system_action=True,
                payload={
                    "question_id": str(knockout_question.id) if knockout_question else None,
                    "reason_code": knockout_question.knockout_reason_code if knockout_question else "",
                },
            )


class ScreeningRuleSetViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningRuleSetSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active", "is_template"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return ScreeningRuleSet.objects.filter(
            tenant_id=self.request.tenant_id
        ).prefetch_related("rules")

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"], url_path="evaluate/(?P<application_id>[^/.]+)")
    def evaluate(self, request, pk=None, application_id=None):
        """Run this rule set against an application and store the evaluation."""
        from apps.applications.models import Application
        rule_set = self.get_object()
        try:
            application = Application.objects.get(id=application_id, tenant_id=self.request.tenant_id)
        except Application.DoesNotExist:
            return Response({"error": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        rules = rule_set.rules.all().order_by("order")
        total_score = 0.0
        max_score = sum(r.weight for r in rules)
        passed_rules = []
        failed_rules = []
        knockout_rule = None
        auto_decision = "review"
        explanation = []

        # Simple evaluation engine — field_path lookup against application data
        app_data = {
            "years_experience": getattr(application, "years_experience", None),
            "current_stage": application.current_stage if hasattr(application, "current_stage") else None,
        }

        for rule in rules:
            passed = False
            value = app_data.get(rule.field_path)
            op = rule.operator
            ev = rule.expected_value

            try:
                if op == "exists":
                    passed = value is not None
                elif op == "not_exists":
                    passed = value is None
                elif value is None:
                    passed = False
                elif op == "eq":
                    passed = str(value) == str(ev)
                elif op == "neq":
                    passed = str(value) != str(ev)
                elif op == "gte":
                    passed = float(value) >= float(ev)
                elif op == "lte":
                    passed = float(value) <= float(ev)
                elif op == "contains":
                    passed = str(ev).lower() in str(value).lower()
                elif op == "not_contains":
                    passed = str(ev).lower() not in str(value).lower()
                elif op == "in":
                    passed = str(value) in [str(x) for x in (ev or [])]
                elif op == "not_in":
                    passed = str(value) not in [str(x) for x in (ev or [])]
            except (TypeError, ValueError):
                passed = False

            entry = {"rule_id": str(rule.id), "type": rule.rule_type, "field": rule.field_path, "passed": passed}
            if passed:
                total_score += rule.weight
                passed_rules.append(entry)
            else:
                failed_rules.append(entry)
                if rule.is_knockout:
                    knockout_rule = rule
                    auto_decision = "reject"
                    explanation.append(f"KNOCKOUT: {rule.description or rule.field_path} failed.")
                    break

            explanation.append(f"{'PASS' if passed else 'FAIL'}: {rule.description or rule.field_path}")

        if knockout_rule is None:
            if rule_set.auto_advance_threshold and total_score >= rule_set.auto_advance_threshold:
                auto_decision = "advance"
            elif rule_set.auto_reject_threshold and total_score < rule_set.auto_reject_threshold:
                auto_decision = "reject"

        evaluation = ScreeningRuleEvaluation.objects.create(
            tenant_id=self.request.tenant_id,
            application=application,
            rule_set=rule_set,
            total_score=round(total_score, 2),
            max_possible_score=round(max_score, 2),
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            knockout_rule=knockout_rule,
            auto_decision=auto_decision,
            explanation_payload={"steps": explanation},
        )
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=application,
            action="rule_evaluation_run",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            is_system_action=False,
            payload={
                "rule_set_id": str(rule_set.id),
                "auto_decision": auto_decision,
                "score": total_score,
            },
        )
        return Response(ScreeningRuleEvaluationSerializer(evaluation).data, status=status.HTTP_201_CREATED)


class ScreeningRuleViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningRuleSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["rule_type", "is_knockout"]

    def get_queryset(self):
        qs = ScreeningRule.objects.filter(
            rule_set__tenant_id=self.request.tenant_id
        )
        rule_set_id = self.request.query_params.get("rule_set")
        if rule_set_id:
            qs = qs.filter(rule_set_id=rule_set_id)
        return qs.order_by("order")


class ScreeningRuleEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScreeningRuleEvaluationSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["auto_decision"]

    def get_queryset(self):
        qs = ScreeningRuleEvaluation.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("rule_set")
        application_id = self.request.query_params.get("application")
        if application_id:
            qs = qs.filter(application_id=application_id)
        return qs


class CredentialVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = CredentialVerificationSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "verification_method"]
    search_fields = ["credential_type", "credential_number", "issuing_authority"]

    def get_queryset(self):
        return CredentialVerification.objects.filter(
            tenant_id=self.request.tenant_id
        )

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        """Mark a credential as verified."""
        credential = self.get_object()
        credential.status = "verified"
        credential.verified_by = request.user
        credential.verified_at = timezone.now()
        credential.notes = request.data.get("notes", credential.notes)
        credential.save(update_fields=["status", "verified_by", "verified_at", "notes", "updated_at"])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=credential.application,
            action="credential_verified",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            payload={"credential_type": credential.credential_type, "status": "verified"},
        )
        return Response(CredentialVerificationSerializer(credential).data)

    @action(detail=True, methods=["post"], url_path="fail")
    def fail_verification(self, request, pk=None):
        """Mark a credential verification as failed."""
        credential = self.get_object()
        credential.status = "failed"
        credential.notes = request.data.get("notes", credential.notes)
        credential.save(update_fields=["status", "notes", "updated_at"])
        return Response(CredentialVerificationSerializer(credential).data)


class ScreeningDecisionReasonViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningDecisionReasonSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["category", "is_active", "requires_documentation", "is_protected_class_sensitive"]
    search_fields = ["code", "label", "description"]

    def get_queryset(self):
        return ScreeningDecisionReason.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class ScreeningDecisionViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningDecisionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["decision", "is_automated", "blind_review_active"]

    def get_queryset(self):
        qs = ScreeningDecision.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("reason", "decided_by")
        application_id = self.request.query_params.get("application")
        if application_id:
            qs = qs.filter(application_id=application_id)
        return qs

    def perform_create(self, serializer):
        decision = serializer.save(
            tenant_id=self.request.tenant_id,
            decided_by=self.request.user,
            is_automated=False,
        )
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=decision.application,
            action="human_decision_made",
            actor=self.request.user,
            actor_label=f"{self.request.user.first_name} {self.request.user.last_name}",
            payload={
                "decision": decision.decision,
                "reason_code": decision.reason.code,
                "blind_review": decision.blind_review_active,
            },
        )

    @action(detail=True, methods=["post"], url_path="override")
    def override(self, request, pk=None):
        """Override a decision (e.g. after appeal)."""
        decision = self.get_object()
        old_decision = decision.decision
        decision.decision = request.data.get("decision", decision.decision)
        decision.notes = request.data.get("notes", decision.notes)
        decision.explanation_summary = request.data.get("explanation_summary", decision.explanation_summary)
        decision.save(update_fields=["decision", "notes", "explanation_summary", "updated_at"])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=decision.application,
            action="decision_overridden",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            payload={"old_decision": old_decision, "new_decision": decision.decision},
        )
        return Response(ScreeningDecisionSerializer(decision).data)


class ScreenReviewQueueViewSet(viewsets.ModelViewSet):
    serializer_class = ScreenReviewQueueSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "priority", "blind_review_mode"]
    ordering_fields = ["priority", "created_at", "due_by"]

    def get_queryset(self):
        qs = ScreenReviewQueue.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("assigned_to", "application")
        # Reviewers see only their assigned items unless admin/recruiter
        assigned_to_me = self.request.query_params.get("mine")
        if assigned_to_me == "true":
            qs = qs.filter(assigned_to=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        """Assign a queue entry to a reviewer."""
        entry = self.get_object()
        from apps.accounts.models import User
        reviewer_id = request.data.get("reviewer_id")
        try:
            reviewer = User.objects.get(id=reviewer_id, tenant_id=self.request.tenant_id)
        except User.DoesNotExist:
            return Response({"error": "Reviewer not found."}, status=status.HTTP_404_NOT_FOUND)
        entry.assigned_to = reviewer
        entry.status = "assigned"
        entry.save(update_fields=["assigned_to", "status", "updated_at"])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=entry.application,
            action="queue_assigned",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            payload={"reviewer_id": str(reviewer_id)},
        )
        return Response(ScreenReviewQueueSerializer(entry).data)

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        """Mark review as started."""
        entry = self.get_object()
        entry.status = "in_review"
        entry.review_started_at = timezone.now()
        entry.save(update_fields=["status", "review_started_at", "updated_at"])
        return Response(ScreenReviewQueueSerializer(entry).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_review(self, request, pk=None):
        """Mark review as completed."""
        entry = self.get_object()
        entry.status = "completed"
        entry.review_completed_at = timezone.now()
        entry.save(update_fields=["status", "review_completed_at", "updated_at"])
        return Response(ScreenReviewQueueSerializer(entry).data)

    @action(detail=True, methods=["post"], url_path="escalate")
    def escalate(self, request, pk=None):
        """Escalate a review queue entry."""
        entry = self.get_object()
        entry.status = "escalated"
        entry.notes = request.data.get("notes", entry.notes)
        entry.save(update_fields=["status", "notes", "updated_at"])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=entry.application,
            action="queue_escalated",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            payload={"notes": entry.notes},
        )
        return Response(ScreenReviewQueueSerializer(entry).data)

    @action(detail=True, methods=["post"], url_path="toggle-blind-review")
    def toggle_blind_review(self, request, pk=None):
        """Toggle blind review mode on a queue entry."""
        entry = self.get_object()
        entry.blind_review_mode = not entry.blind_review_mode
        entry.save(update_fields=["blind_review_mode", "updated_at"])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=entry.application,
            action="blind_review_toggled",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            payload={"blind_review_mode": entry.blind_review_mode},
        )
        return Response({"blind_review_mode": entry.blind_review_mode})


class ScreeningAuditEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScreeningAuditEntrySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["action", "is_system_action"]
    ordering_fields = ["occurred_at"]

    def get_queryset(self):
        qs = ScreeningAuditEntry.objects.filter(tenant_id=self.request.tenant_id)
        application_id = self.request.query_params.get("application")
        if application_id:
            qs = qs.filter(application_id=application_id)
        return qs.select_related("actor")


class ScreeningAppealViewSet(viewsets.ModelViewSet):
    serializer_class = ScreeningAppealSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status"]

    def get_queryset(self):
        return ScreeningAppeal.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("original_decision", "assigned_reviewer")

    def perform_create(self, serializer):
        appeal = serializer.save(tenant_id=self.request.tenant_id)
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=appeal.application,
            action="appeal_submitted",
            is_system_action=True,
            payload={"appeal_id": str(appeal.id)},
        )

    @action(detail=True, methods=["post"], url_path="review")
    def review_appeal(self, request, pk=None):
        """Record a reviewer's decision on an appeal."""
        appeal = self.get_object()
        outcome = request.data.get("outcome")  # upheld | overturned | closed
        if outcome not in ("upheld", "overturned", "closed"):
            return Response({"error": "outcome must be upheld, overturned, or closed."}, status=status.HTTP_400_BAD_REQUEST)
        appeal.status = outcome
        appeal.reviewer_notes = request.data.get("reviewer_notes", appeal.reviewer_notes)
        appeal.outcome_explanation = request.data.get("outcome_explanation", appeal.outcome_explanation)
        appeal.reviewed_at = timezone.now()
        appeal.assigned_reviewer = request.user
        appeal.save(update_fields=[
            "status", "reviewer_notes", "outcome_explanation",
            "reviewed_at", "assigned_reviewer", "updated_at",
        ])
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=appeal.application,
            action="appeal_reviewed",
            actor=request.user,
            actor_label=f"{request.user.first_name} {request.user.last_name}",
            payload={"outcome": outcome, "appeal_id": str(appeal.id)},
        )
        # If overturned, override the original screening decision
        if outcome == "overturned":
            original = appeal.original_decision
            original.decision = "advance"
            original.notes = f"Overturned by appeal {appeal.id}"
            original.save(update_fields=["decision", "notes", "updated_at"])
            ScreeningAuditEntry.objects.create(
                tenant_id=self.request.tenant_id,
                application=appeal.application,
                action="decision_overridden",
                actor=request.user,
                actor_label=f"{request.user.first_name} {request.user.last_name}",
                payload={"appeal_id": str(appeal.id), "new_decision": "advance"},
            )
        return Response(ScreeningAppealSerializer(appeal).data)

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw_appeal(self, request, pk=None):
        """Candidate withdraws the appeal."""
        appeal = self.get_object()
        appeal.status = "withdrawn"
        appeal.save(update_fields=["status", "updated_at"])
        return Response(ScreeningAppealSerializer(appeal).data)


class ExplainableMatchSnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = ExplainableMatchSnapshotSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        qs = ExplainableMatchSnapshot.objects.filter(tenant_id=self.request.tenant_id)
        application_id = self.request.query_params.get("application")
        if application_id:
            qs = qs.filter(application_id=application_id)
        return qs

    def perform_create(self, serializer):
        snapshot = serializer.save(tenant_id=self.request.tenant_id)
        ScreeningAuditEntry.objects.create(
            tenant_id=self.request.tenant_id,
            application=snapshot.application,
            action="explanation_generated",
            is_system_action=True,
            payload={"snapshot_id": str(snapshot.id), "score": snapshot.overall_match_score},
        )


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
# Existing
router.register("vendors", AssessmentVendorViewSet, basename="assessment-vendors")
router.register("catalog", AssessmentCatalogItemViewSet, basename="assessment-catalog")
router.register("orders", AssessmentOrderViewSet, basename="assessment-orders")
router.register("results", AssessmentResultViewSet, basename="assessment-results")
router.register("waivers", AssessmentWaiverViewSet, basename="assessment-waivers")
router.register("alternate-paths", AlternateAssessmentPathViewSet, basename="alternate-assessment-paths")
# New
router.register("questionnaires", ScreeningQuestionnaireViewSet, basename="screening-questionnaires")
router.register("questions", ScreeningQuestionViewSet, basename="screening-questions")
router.register("questionnaire-responses", ScreeningQuestionnaireResponseViewSet, basename="questionnaire-responses")
router.register("rule-sets", ScreeningRuleSetViewSet, basename="screening-rule-sets")
router.register("rules", ScreeningRuleViewSet, basename="screening-rules")
router.register("rule-evaluations", ScreeningRuleEvaluationViewSet, basename="screening-rule-evaluations")
router.register("credentials", CredentialVerificationViewSet, basename="credential-verifications")
router.register("decision-reasons", ScreeningDecisionReasonViewSet, basename="screening-decision-reasons")
router.register("decisions", ScreeningDecisionViewSet, basename="screening-decisions")
router.register("review-queue", ScreenReviewQueueViewSet, basename="screen-review-queue")
router.register("audit", ScreeningAuditEntryViewSet, basename="screening-audit")
router.register("appeals", ScreeningAppealViewSet, basename="screening-appeals")
router.register("match-snapshots", ExplainableMatchSnapshotViewSet, basename="match-snapshots")

urlpatterns = [
    path("", include(router.urls)),
]
