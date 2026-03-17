"""Portal app API — Feature 5: Candidate Experience Portal 2.0.

All portal public endpoints plus admin ViewSets for every new model.
The existing shared/views/portal.py endpoints are preserved and re-exported
via portal_urlpatterns so backward-compat is maintained.
"""

import secrets
from django.utils import timezone
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from django.urls import path, include

from apps.portal.models import (
    JobAlert,
    CandidateFeedback,
    PortalToken,
    SavedApplicationDraft,
    CandidateNPS,
    AccessibilityPreference,
    RoleApplicationForm,
    CandidateDashboardSession,
    ApplicationStageConfig,
    InterviewPrepPacket,
    SelfRescheduleRule,
    CandidateWithdrawal,
    MissingDocumentRequest,
    AccommodationRequest,
    TalentCommunityMember,
    CandidateEvent,
    EventRegistration,
    HelpArticle,
    ConsentRecord,
    DataSubjectRequest,
    RecruiterSafeRoute,
)


# ── Pagination ────────────────────────────────────────────────────────────────

class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


# ── Serializers ───────────────────────────────────────────────────────────────

class JobAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAlert
        fields = [
            "id", "email", "name", "keywords", "department", "location",
            "employment_type", "salary_min", "frequency",
            "is_active", "last_notified_at", "unsubscribe_token", "created_at",
        ]
        read_only_fields = ["id", "last_notified_at", "unsubscribe_token", "created_at"]


class CandidateFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateFeedback
        fields = [
            "id", "candidate", "application", "overall_rating",
            "comments", "would_apply_again", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PortalTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalToken
        fields = [
            "id", "candidate", "application", "purpose",
            "expires_at", "used_at", "created_at",
        ]
        read_only_fields = ["id", "used_at", "created_at"]


class SavedApplicationDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedApplicationDraft
        fields = [
            "id", "candidate", "job", "session_key",
            "draft_data", "resume_file_url", "autofill_source",
            "completion_pct", "last_saved_at", "created_at",
        ]
        read_only_fields = ["id", "last_saved_at", "created_at"]


class CandidateNPSSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateNPS
        fields = [
            "id", "candidate", "application", "event",
            "score", "comment", "responded_at",
        ]
        read_only_fields = ["id", "responded_at"]


class AccessibilityPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityPreference
        fields = [
            "id", "candidate", "needs", "notes", "auth_alternative",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RoleApplicationFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleApplicationForm
        fields = [
            "id", "name", "job", "department", "fields",
            "enable_autofill", "one_click_threshold",
            "supported_locales", "legal_notices", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CandidateDashboardSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateDashboardSession
        fields = [
            "id", "candidate", "login_method", "ip_address",
            "expires_at", "last_activity_at", "created_at",
        ]
        read_only_fields = ["id", "last_activity_at", "created_at"]


class ApplicationStageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStageConfig
        fields = [
            "id", "stage", "candidate_label", "description",
            "expected_timeline_days", "next_steps_message",
            "translations", "show_interviewer_names", "show_timeline",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InterviewPrepPacketSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewPrepPacket
        fields = [
            "id", "application", "interview", "title",
            "sections", "logistics", "accessibility_notes",
            "sent_at", "viewed_at",
            "help_contact_name", "help_contact_email", "help_contact_phone",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SelfRescheduleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SelfRescheduleRule
        fields = [
            "id", "job", "max_reschedules", "min_hours_before",
            "allowed_interview_types", "require_reason",
            "notify_recruiter", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CandidateWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateWithdrawal
        fields = [
            "id", "application", "reason", "reason_detail",
            "would_apply_future", "withdrawn_at",
        ]
        read_only_fields = ["id", "withdrawn_at"]


class MissingDocumentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissingDocumentRequest
        fields = [
            "id", "application", "requested_by", "document_type",
            "instructions", "upload_token", "status",
            "uploaded_file_url", "due_date", "sent_at", "uploaded_at", "created_at",
        ]
        read_only_fields = ["id", "upload_token", "created_at"]


class AccommodationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationRequest
        fields = [
            "id", "candidate", "application", "accommodation_type",
            "description", "needs", "status",
            "reviewer", "reviewer_notes", "approved_accommodations",
            "reviewed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TalentCommunityMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentCommunityMember
        fields = [
            "id", "candidate", "email", "name", "interests",
            "preferred_roles", "preferred_locations", "open_to_relocation",
            "linkedin_url", "status", "assigned_recruiter",
            "consent_marketing", "consent_given_at",
            "unsubscribe_token", "joined_at", "updated_at",
        ]
        read_only_fields = ["id", "unsubscribe_token", "joined_at", "updated_at"]


class CandidateEventSerializer(serializers.ModelSerializer):
    registration_count = serializers.SerializerMethodField()

    class Meta:
        model = CandidateEvent
        fields = [
            "id", "title", "event_type", "description",
            "starts_at", "ends_at", "location", "is_virtual", "virtual_link",
            "max_registrants", "is_public", "accessibility_info",
            "registration_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_registration_count(self, obj):
        return obj.registrations.count()


class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = [
            "id", "event", "candidate", "email", "name",
            "accessibility_needs", "attended", "registered_at",
        ]
        read_only_fields = ["id", "registered_at"]


class HelpArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpArticle
        fields = [
            "id", "category", "title", "slug", "content",
            "translations", "is_published", "is_pinned",
            "view_count", "helpful_votes", "unhelpful_votes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "view_count", "helpful_votes", "unhelpful_votes", "created_at", "updated_at"]


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = [
            "id", "candidate", "purpose", "granted",
            "granted_at", "withdrawn_at", "locale",
            "notice_text", "notice_version", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DataSubjectRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSubjectRequest
        fields = [
            "id", "candidate", "email", "request_type", "description",
            "status", "handler", "response_notes", "due_date",
            "completed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RecruiterSafeRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterSafeRoute
        fields = [
            "id", "department", "location", "recruiter",
            "recruiter_display_name", "recruiter_display_email",
            "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class JobAlertViewSet(viewsets.ModelViewSet):
    """Admin: manage job alert subscriptions."""
    permission_classes = [IsAuthenticated]
    serializer_class = JobAlertSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = JobAlert.objects.filter(tenant=self.request.user.tenant)
        if email := self.request.query_params.get("email"):
            qs = qs.filter(email__icontains=email)
        if active := self.request.query_params.get("is_active"):
            qs = qs.filter(is_active=active.lower() == "true")
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        token = secrets.token_urlsafe(32)
        serializer.save(tenant=self.request.user.tenant, unsubscribe_token=token)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        alert = self.get_object()
        alert.is_active = False
        alert.save(update_fields=["is_active"])
        return Response({"status": "deactivated"})


class CandidateFeedbackViewSet(viewsets.ModelViewSet):
    """Admin: view candidate feedback and NPS."""
    permission_classes = [IsAuthenticated]
    serializer_class = CandidateFeedbackSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return CandidateFeedback.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("candidate", "application").order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        from django.db.models import Avg, Count
        qs = self.get_queryset()
        agg = qs.aggregate(avg_rating=Avg("overall_rating"), count=Count("id"))
        would_apply = qs.filter(would_apply_again=True).count()
        return Response({
            "total": agg["count"],
            "avg_rating": round(agg["avg_rating"] or 0, 2),
            "would_apply_again_pct": round((would_apply / agg["count"] * 100) if agg["count"] else 0, 1),
        })


class CandidateNPSViewSet(viewsets.ModelViewSet):
    """Admin: view and manage candidate NPS responses."""
    permission_classes = [IsAuthenticated]
    serializer_class = CandidateNPSSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return CandidateNPS.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("candidate", "application").order_by("-responded_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        from django.db.models import Avg, Count
        qs = self.get_queryset()
        agg = qs.aggregate(avg_score=Avg("score"), count=Count("id"))
        promoters = qs.filter(score__gte=9).count()
        detractors = qs.filter(score__lte=6).count()
        total = agg["count"] or 1
        nps = round(((promoters - detractors) / total) * 100, 1)
        return Response({
            "total": agg["count"],
            "avg_score": round(agg["avg_score"] or 0, 2),
            "nps_score": nps,
            "promoters": promoters,
            "detractors": detractors,
            "passives": total - promoters - detractors,
        })


class SavedApplicationDraftViewSet(viewsets.ModelViewSet):
    """Admin: view and manage saved application drafts."""
    permission_classes = [IsAuthenticated]
    serializer_class = SavedApplicationDraftSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return SavedApplicationDraft.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("candidate", "job").order_by("-last_saved_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class AccessibilityPreferenceViewSet(viewsets.ModelViewSet):
    """Admin: view and manage candidate accessibility preferences."""
    permission_classes = [IsAuthenticated]
    serializer_class = AccessibilityPreferenceSerializer

    def get_queryset(self):
        return AccessibilityPreference.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("candidate")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class RoleApplicationFormViewSet(viewsets.ModelViewSet):
    """Admin: manage role-based application forms."""
    permission_classes = [IsAuthenticated]
    serializer_class = RoleApplicationFormSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = RoleApplicationForm.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("active_only") == "true":
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        form = self.get_object()
        form.pk = None
        form.name = f"Copy of {form.name}"
        form.save()
        return Response(RoleApplicationFormSerializer(form).data, status=status.HTTP_201_CREATED)


class ApplicationStageConfigViewSet(viewsets.ModelViewSet):
    """Admin: configure candidate-facing stage descriptions and timelines."""
    permission_classes = [IsAuthenticated]
    serializer_class = ApplicationStageConfigSerializer

    def get_queryset(self):
        return ApplicationStageConfig.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("stage")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class InterviewPrepPacketViewSet(viewsets.ModelViewSet):
    """Admin: create and manage interview prep packets."""
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewPrepPacketSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = InterviewPrepPacket.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("application", "interview")
        if app_id := self.request.query_params.get("application"):
            qs = qs.filter(application_id=app_id)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        packet = self.get_object()
        packet.sent_at = timezone.now()
        packet.save(update_fields=["sent_at"])
        return Response({"status": "sent", "sent_at": packet.sent_at})

    @action(detail=True, methods=["post"])
    def mark_viewed(self, request, pk=None):
        packet = self.get_object()
        if not packet.viewed_at:
            packet.viewed_at = timezone.now()
            packet.save(update_fields=["viewed_at"])
        return Response({"status": "viewed", "viewed_at": packet.viewed_at})


class SelfRescheduleRuleViewSet(viewsets.ModelViewSet):
    """Admin: configure self-reschedule rules per job/tenant."""
    permission_classes = [IsAuthenticated]
    serializer_class = SelfRescheduleRuleSerializer

    def get_queryset(self):
        return SelfRescheduleRule.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("job")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class CandidateWithdrawalViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin: view self-withdrawals."""
    permission_classes = [IsAuthenticated]
    serializer_class = CandidateWithdrawalSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return CandidateWithdrawal.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("application").order_by("-withdrawn_at")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        from django.db.models import Count
        qs = self.get_queryset()
        by_reason = list(qs.values("reason").annotate(count=Count("id")).order_by("-count"))
        return Response({"total": qs.count(), "by_reason": by_reason})


class MissingDocumentRequestViewSet(viewsets.ModelViewSet):
    """Admin: request and track missing documents from candidates."""
    permission_classes = [IsAuthenticated]
    serializer_class = MissingDocumentRequestSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = MissingDocumentRequest.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("application", "requested_by")
        if app_id := self.request.query_params.get("application"):
            qs = qs.filter(application_id=app_id)
        if s := self.request.query_params.get("status"):
            qs = qs.filter(status=s)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        token = secrets.token_urlsafe(64)
        serializer.save(
            tenant=self.request.user.tenant,
            requested_by=self.request.user,
            upload_token=token,
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        req = self.get_object()
        req.sent_at = timezone.now()
        req.save(update_fields=["sent_at"])
        return Response({"status": "sent"})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        req = self.get_object()
        req.status = "cancelled"
        req.save(update_fields=["status"])
        return Response({"status": "cancelled"})


class AccommodationRequestViewSet(viewsets.ModelViewSet):
    """Admin: manage candidate accommodation requests."""
    permission_classes = [IsAuthenticated]
    serializer_class = AccommodationRequestSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = AccommodationRequest.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("candidate", "application", "reviewer")
        if s := self.request.query_params.get("status"):
            qs = qs.filter(status=s)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        req.status = "approved"
        req.reviewer = request.user
        req.reviewer_notes = request.data.get("notes", "")
        req.approved_accommodations = request.data.get("approved_accommodations", [])
        req.reviewed_at = timezone.now()
        req.save(update_fields=["status", "reviewer", "reviewer_notes",
                                "approved_accommodations", "reviewed_at", "updated_at"])
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        req = self.get_object()
        req.status = "declined"
        req.reviewer = request.user
        req.reviewer_notes = request.data.get("notes", "")
        req.reviewed_at = timezone.now()
        req.save(update_fields=["status", "reviewer", "reviewer_notes", "reviewed_at", "updated_at"])
        return Response({"status": "declined"})

    @action(detail=True, methods=["post"])
    def needs_info(self, request, pk=None):
        req = self.get_object()
        req.status = "needs_info"
        req.reviewer_notes = request.data.get("notes", "")
        req.save(update_fields=["status", "reviewer_notes", "updated_at"])
        return Response({"status": "needs_info"})


class TalentCommunityMemberViewSet(viewsets.ModelViewSet):
    """Admin: manage talent community members."""
    permission_classes = [IsAuthenticated]
    serializer_class = TalentCommunityMemberSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = TalentCommunityMember.objects.filter(tenant=self.request.user.tenant)
        if s := self.request.query_params.get("status"):
            qs = qs.filter(status=s)
        if q := self.request.query_params.get("search"):
            qs = qs.filter(email__icontains=q) | qs.filter(name__icontains=q)
        return qs.order_by("-joined_at")

    def perform_create(self, serializer):
        token = secrets.token_urlsafe(32)
        serializer.save(tenant=self.request.user.tenant, unsubscribe_token=token)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        member = self.get_object()
        member.status = "converted"
        member.save(update_fields=["status", "updated_at"])
        return Response({"status": "converted"})

    @action(detail=True, methods=["post"])
    def assign_recruiter(self, request, pk=None):
        member = self.get_object()
        recruiter_id = request.data.get("recruiter_id")
        if not recruiter_id:
            return Response({"error": "recruiter_id required"}, status=status.HTTP_400_BAD_REQUEST)
        member.assigned_recruiter_id = recruiter_id
        member.save(update_fields=["assigned_recruiter", "updated_at"])
        return Response({"status": "assigned"})


class CandidateEventViewSet(viewsets.ModelViewSet):
    """Admin: manage recruiting events."""
    permission_classes = [IsAuthenticated]
    serializer_class = CandidateEventSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = CandidateEvent.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("upcoming") == "true":
            qs = qs.filter(starts_at__gte=timezone.now())
        return qs.order_by("starts_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["get"])
    def registrations(self, request, pk=None):
        event = self.get_object()
        regs = EventRegistration.objects.filter(event=event)
        ser = EventRegistrationSerializer(regs, many=True)
        return Response({"count": regs.count(), "results": ser.data})

    @action(detail=True, methods=["post"])
    def mark_attended(self, request, pk=None):
        event = self.get_object()
        email = request.data.get("email")
        attended = request.data.get("attended", True)
        updated = EventRegistration.objects.filter(event=event, email=email).update(attended=attended)
        return Response({"updated": updated})


class EventRegistrationViewSet(viewsets.ModelViewSet):
    """Admin: manage event registrations."""
    permission_classes = [IsAuthenticated]
    serializer_class = EventRegistrationSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = EventRegistration.objects.filter(tenant=self.request.user.tenant)
        if event_id := self.request.query_params.get("event"):
            qs = qs.filter(event_id=event_id)
        return qs.order_by("-registered_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class HelpArticleViewSet(viewsets.ModelViewSet):
    """Admin: manage help center articles."""
    permission_classes = [IsAuthenticated]
    serializer_class = HelpArticleSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = HelpArticle.objects.filter(
            tenant=self.request.user.tenant
        ) | HelpArticle.objects.filter(tenant__isnull=True)
        if cat := self.request.query_params.get("category"):
            qs = qs.filter(category=cat)
        if self.request.query_params.get("published_only") == "true":
            qs = qs.filter(is_published=True)
        if q := self.request.query_params.get("search"):
            qs = qs.filter(title__icontains=q)
        return qs.order_by("-is_pinned", "-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def vote(self, request, pk=None):
        article = self.get_object()
        helpful = request.data.get("helpful", True)
        if helpful:
            article.helpful_votes += 1
        else:
            article.unhelpful_votes += 1
        article.save(update_fields=["helpful_votes", "unhelpful_votes"])
        return Response({"helpful_votes": article.helpful_votes, "unhelpful_votes": article.unhelpful_votes})


class ConsentRecordViewSet(viewsets.ModelViewSet):
    """Admin: view and manage candidate consent records."""
    permission_classes = [IsAuthenticated]
    serializer_class = ConsentRecordSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = ConsentRecord.objects.filter(tenant=self.request.user.tenant)
        if cand := self.request.query_params.get("candidate"):
            qs = qs.filter(candidate_id=cand)
        if purpose := self.request.query_params.get("purpose"):
            qs = qs.filter(purpose=purpose)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        record = self.get_object()
        record.granted = False
        record.withdrawn_at = timezone.now()
        record.save(update_fields=["granted", "withdrawn_at"])
        return Response({"status": "withdrawn"})


class DataSubjectRequestViewSet(viewsets.ModelViewSet):
    """Admin: manage GDPR/CCPA data subject requests."""
    permission_classes = [IsAuthenticated]
    serializer_class = DataSubjectRequestSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = DataSubjectRequest.objects.filter(tenant=self.request.user.tenant)
        if s := self.request.query_params.get("status"):
            qs = qs.filter(status=s)
        if rt := self.request.query_params.get("request_type"):
            qs = qs.filter(request_type=rt)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        from datetime import timedelta, date
        due = date.today() + timedelta(days=30)
        serializer.save(tenant=self.request.user.tenant, due_date=due)

    @action(detail=True, methods=["post"])
    def start_review(self, request, pk=None):
        dsr = self.get_object()
        dsr.status = "in_progress"
        dsr.handler = request.user
        dsr.save(update_fields=["status", "handler", "updated_at"])
        return Response({"status": "in_progress"})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        dsr = self.get_object()
        dsr.status = "completed"
        dsr.response_notes = request.data.get("notes", "")
        dsr.completed_at = timezone.now()
        dsr.save(update_fields=["status", "response_notes", "completed_at", "updated_at"])
        return Response({"status": "completed"})

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        from datetime import timedelta
        dsr = self.get_object()
        dsr.status = "extended"
        if dsr.due_date:
            from datetime import date
            dsr.due_date = dsr.due_date + timedelta(days=30)
        dsr.save(update_fields=["status", "due_date", "updated_at"])
        return Response({"status": "extended", "new_due_date": str(dsr.due_date)})


class RecruiterSafeRouteViewSet(viewsets.ModelViewSet):
    """Admin: configure recruiter safe-routing rules."""
    permission_classes = [IsAuthenticated]
    serializer_class = RecruiterSafeRouteSerializer

    def get_queryset(self):
        return RecruiterSafeRoute.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("recruiter")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


# ── Public portal endpoints (AllowAny) ────────────────────────────────────────

class PublicPortalWithdrawView(APIView):
    """Candidate self-withdraws via signed token."""
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt
        from django.conf import settings

        token = request.data.get("token")
        if not token:
            return Response({"error": "token required"}, status=400)
        portal_secret = getattr(settings, "PORTAL_SECRET_KEY", settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "withdraw":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        from apps.applications.models import Application
        try:
            app = Application.objects.get(
                id=payload["application_id"], tenant_id=payload["tenant_id"]
            )
        except Application.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        if app.status == "withdrawn":
            return Response({"error": "Already withdrawn"}, status=409)

        app.status = "withdrawn"
        app.save(update_fields=["status", "updated_at"])

        withdrawal = CandidateWithdrawal.objects.create(
            tenant_id=payload["tenant_id"],
            application=app,
            reason=request.data.get("reason", ""),
            reason_detail=request.data.get("reason_detail", ""),
            would_apply_future=request.data.get("would_apply_future"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return Response({"status": "withdrawn", "withdrawal_id": str(withdrawal.id)})


class PublicNPSSurveyView(APIView):
    """Candidate submits NPS survey via signed token."""
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt
        from django.conf import settings

        token = request.data.get("token")
        if not token:
            return Response({"error": "token required"}, status=400)
        portal_secret = getattr(settings, "PORTAL_SECRET_KEY", settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "nps_survey":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        score = request.data.get("score")
        if score is None or not (0 <= int(score) <= 10):
            return Response({"error": "score 0-10 required"}, status=400)

        nps = CandidateNPS.objects.create(
            tenant_id=payload["tenant_id"],
            candidate_id=payload["candidate_id"],
            application_id=payload.get("application_id"),
            event=payload.get("event", "applied"),
            score=int(score),
            comment=request.data.get("comment", ""),
        )
        return Response({"id": str(nps.id), "status": "recorded"}, status=201)


class PublicAccommodationRequestView(APIView):
    """Candidate submits an accommodation request (public, no login)."""
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.tenants.models import Tenant
        from apps.candidates.models import Candidate

        tenant_slug = request.data.get("tenant_slug", "")
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Response({"error": "Company not found"}, status=404)

        email = request.data.get("email", "")
        candidate = None
        try:
            from apps.candidates.models import CandidateIdentity
            identity = CandidateIdentity.objects.get(
                tenant=tenant, identity_type="email", identity_value=email.lower()
            )
            candidate = identity.candidate
        except Exception:
            pass

        req = AccommodationRequest.objects.create(
            tenant=tenant,
            candidate=candidate,
            application_id=request.data.get("application_id"),
            accommodation_type=request.data.get("accommodation_type", "other"),
            description=request.data.get("description", ""),
            needs=request.data.get("needs", []),
        )
        return Response({"id": str(req.id), "status": "submitted"}, status=201)


class PublicConsentView(APIView):
    """Candidate grants or withdraws consent (public, token-gated)."""
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt
        from django.conf import settings

        token = request.data.get("token")
        if not token:
            return Response({"error": "token required"}, status=400)
        portal_secret = getattr(settings, "PORTAL_SECRET_KEY", settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        purpose = request.data.get("purpose")
        granted = request.data.get("granted", True)

        record = ConsentRecord.objects.create(
            tenant_id=payload["tenant_id"],
            candidate_id=payload["candidate_id"],
            purpose=purpose,
            granted=granted,
            granted_at=timezone.now() if granted else None,
            withdrawn_at=timezone.now() if not granted else None,
            ip_address=request.META.get("REMOTE_ADDR"),
            locale=request.data.get("locale", "en"),
            notice_text=request.data.get("notice_text", ""),
            notice_version=request.data.get("notice_version", ""),
        )
        return Response({"id": str(record.id), "status": "recorded"}, status=201)


class PublicDSRView(APIView):
    """Candidate submits a GDPR data subject request (public)."""
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.tenants.models import Tenant
        from datetime import timedelta, date

        tenant_slug = request.data.get("tenant_slug", "")
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Response({"error": "Company not found"}, status=404)

        email = request.data.get("email", "")
        if not email:
            return Response({"error": "email required"}, status=400)

        request_type = request.data.get("request_type", "access")

        dsr = DataSubjectRequest.objects.create(
            tenant=tenant,
            email=email,
            request_type=request_type,
            description=request.data.get("description", ""),
            due_date=date.today() + timedelta(days=30),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({
            "id": str(dsr.id),
            "status": "submitted",
            "due_date": str(dsr.due_date),
        }, status=201)


class PublicCommunityJoinView(APIView):
    """Candidate joins the talent community (public)."""
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.tenants.models import Tenant

        tenant_slug = request.data.get("tenant_slug", "")
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Response({"error": "Company not found"}, status=404)

        email = request.data.get("email", "")
        if not email:
            return Response({"error": "email required"}, status=400)

        member, created = TalentCommunityMember.objects.get_or_create(
            tenant=tenant,
            email=email,
            defaults={
                "name": request.data.get("name", ""),
                "interests": request.data.get("interests", []),
                "preferred_roles": request.data.get("preferred_roles", []),
                "preferred_locations": request.data.get("preferred_locations", []),
                "open_to_relocation": request.data.get("open_to_relocation", False),
                "linkedin_url": request.data.get("linkedin_url", ""),
                "consent_marketing": request.data.get("consent_marketing", False),
                "consent_given_at": timezone.now() if request.data.get("consent_marketing") else None,
                "unsubscribe_token": secrets.token_urlsafe(32),
            },
        )
        if not created:
            member.status = "active"
            member.save(update_fields=["status", "updated_at"])

        return Response({
            "id": str(member.id),
            "created": created,
            "status": member.status,
        }, status=201 if created else 200)


class PublicEventRegisterView(APIView):
    """Candidate registers for a recruiting event (public)."""
    permission_classes = [AllowAny]

    def post(self, request):
        event_id = request.data.get("event_id")
        email = request.data.get("email", "")
        if not event_id or not email:
            return Response({"error": "event_id and email required"}, status=400)

        try:
            event = CandidateEvent.objects.get(id=event_id, is_public=True)
        except CandidateEvent.DoesNotExist:
            return Response({"error": "Event not found"}, status=404)

        if event.max_registrants:
            current = event.registrations.count()
            if current >= event.max_registrants:
                return Response({"error": "Event is full"}, status=409)

        reg, created = EventRegistration.objects.get_or_create(
            event=event,
            email=email,
            defaults={
                "tenant": event.tenant,
                "name": request.data.get("name", ""),
                "accessibility_needs": request.data.get("accessibility_needs", []),
            },
        )
        return Response({
            "id": str(reg.id),
            "event": event.title,
            "registered": created,
        }, status=201 if created else 200)


class PublicHelpSearchView(APIView):
    """Public help center search."""
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.tenants.models import Tenant

        tenant_slug = request.query_params.get("tenant", "")
        q = request.query_params.get("q", "")
        category = request.query_params.get("category", "")

        tenant = None
        if tenant_slug:
            try:
                tenant = Tenant.objects.get(slug=tenant_slug)
            except Tenant.DoesNotExist:
                pass

        qs = HelpArticle.objects.filter(is_published=True)
        if tenant:
            qs = qs.filter(tenant=tenant) | HelpArticle.objects.filter(
                is_published=True, tenant__isnull=True
            )
        else:
            qs = HelpArticle.objects.filter(is_published=True, tenant__isnull=True)

        if q:
            qs = qs.filter(title__icontains=q) | qs.filter(content__icontains=q)
        if category:
            qs = qs.filter(category=category)

        qs = qs.order_by("-is_pinned", "-created_at")[:20]
        ser = HelpArticleSerializer(qs, many=True)
        return Response({"results": ser.data})


class PublicRecruiterContactView(APIView):
    """Public: candidate gets safe-routed recruiter contact info."""
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.tenants.models import Tenant

        tenant_slug = request.query_params.get("tenant", "")
        department = request.query_params.get("department", "")

        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            return Response({"error": "Company not found"}, status=404)

        route = RecruiterSafeRoute.objects.filter(
            tenant=tenant, is_active=True
        ).filter(
            department__icontains=department
        ).first()

        if not route:
            route = RecruiterSafeRoute.objects.filter(
                tenant=tenant, is_active=True, department=""
            ).first()

        if not route:
            return Response({"error": "No recruiter contact configured"}, status=404)

        return Response({
            "name": route.recruiter_display_name or route.recruiter.get_full_name(),
            "email": route.recruiter_display_email or "",
            "department": route.department,
        })


# ── Router + URL patterns ─────────────────────────────────────────────────────

router = DefaultRouter()
router.register("job-alerts", JobAlertViewSet, basename="portal-job-alerts")
router.register("feedback", CandidateFeedbackViewSet, basename="portal-feedback")
router.register("nps", CandidateNPSViewSet, basename="portal-nps")
router.register("drafts", SavedApplicationDraftViewSet, basename="portal-drafts")
router.register("accessibility", AccessibilityPreferenceViewSet, basename="portal-accessibility")
router.register("forms", RoleApplicationFormViewSet, basename="portal-forms")
router.register("stage-configs", ApplicationStageConfigViewSet, basename="portal-stage-configs")
router.register("prep-packets", InterviewPrepPacketViewSet, basename="portal-prep-packets")
router.register("reschedule-rules", SelfRescheduleRuleViewSet, basename="portal-reschedule-rules")
router.register("withdrawals", CandidateWithdrawalViewSet, basename="portal-withdrawals")
router.register("doc-requests", MissingDocumentRequestViewSet, basename="portal-doc-requests")
router.register("accommodations", AccommodationRequestViewSet, basename="portal-accommodations")
router.register("community", TalentCommunityMemberViewSet, basename="portal-community")
router.register("events", CandidateEventViewSet, basename="portal-events")
router.register("event-registrations", EventRegistrationViewSet, basename="portal-event-regs")
router.register("help", HelpArticleViewSet, basename="portal-help")
router.register("consents", ConsentRecordViewSet, basename="portal-consents")
router.register("dsr", DataSubjectRequestViewSet, basename="portal-dsr")
router.register("safe-routes", RecruiterSafeRouteViewSet, basename="portal-safe-routes")

# Re-import legacy public views from shared so they still work
from apps.shared.views.portal import portal_urlpatterns as _legacy_urlpatterns  # noqa: E402

urlpatterns = [
    # New Feature 5 public endpoints
    path("withdraw/", PublicPortalWithdrawView.as_view(), name="portal-withdraw"),
    path("nps-survey/", PublicNPSSurveyView.as_view(), name="portal-nps-survey"),
    path("accommodation/", PublicAccommodationRequestView.as_view(), name="portal-accommodation"),
    path("consent/", PublicConsentView.as_view(), name="portal-consent"),
    path("dsr/submit/", PublicDSRView.as_view(), name="portal-dsr-submit"),
    path("community/join/", PublicCommunityJoinView.as_view(), name="portal-community-join"),
    path("events/register/", PublicEventRegisterView.as_view(), name="portal-event-register"),
    path("help/search/", PublicHelpSearchView.as_view(), name="portal-help-search"),
    path("recruiter-contact/", PublicRecruiterContactView.as_view(), name="portal-recruiter-contact"),
    # Admin ViewSets
    path("admin/", include(router.urls)),
] + _legacy_urlpatterns
