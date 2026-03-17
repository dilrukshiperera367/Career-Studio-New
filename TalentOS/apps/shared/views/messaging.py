"""Messaging API views — MessageViewSet, EmailTemplateViewSet, and OfferLetterTemplateViewSet."""

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.messaging.models import Message, EmailTemplate, OfferLetterTemplate
from apps.messaging.models import NurtureSequence, NurtureStep, NurtureEnrollment, CommunicationPreferenceCenter, BulkCampaign
from apps.accounts.permissions import IsRecruiter, HasTenantAccess, IsTenantAdmin


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id", "candidate", "application", "sender", "channel",
            "direction", "subject", "body", "status", "sent_at", "created_at",
        ]
        read_only_fields = ["id", "status", "sent_at", "created_at"]


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ["id", "slug", "name", "subject", "body", "category", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class OfferLetterTemplateSerializer(serializers.ModelSerializer):
    """Serializer for offer letter template CRUD (#45)."""
    class Meta:
        model = OfferLetterTemplate
        fields = [
            "id", "slug", "name", "subject_line", "html_body",
            "is_default", "is_active", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["candidate", "status", "channel"]

    def get_queryset(self):
        return Message.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        message = serializer.save(
            tenant_id=self.request.tenant_id,
            sender=self.request.user,
            status="queued",
        )
        # Queue for async delivery
        try:
            from apps.messaging.tasks import send_email_task
            send_email_task.delay(str(message.id))
        except Exception:
            pass


class EmailTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]

    def get_queryset(self):
        return EmailTemplate.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class OfferLetterTemplateViewSet(viewsets.ModelViewSet):
    """
    Offer letter template CRUD (#45).
    GET  /api/v1/messaging/offer-templates/         — list templates for this tenant
    POST /api/v1/messaging/offer-templates/         — create a new template
    GET  /api/v1/messaging/offer-templates/<id>/    — retrieve
    PATCH/PUT /api/v1/messaging/offer-templates/<id>/ — update
    DELETE /api/v1/messaging/offer-templates/<id>/  — delete
    POST /api/v1/messaging/offer-templates/<id>/set_default/ — mark as default
    """
    serializer_class = OfferLetterTemplateSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]

    def get_queryset(self):
        return OfferLetterTemplate.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Mark this template as the tenant default; clear default flag on others."""
        template = self.get_object()
        OfferLetterTemplate.objects.filter(
            tenant_id=request.tenant_id, is_default=True
        ).update(is_default=False)
        template.is_default = True
        template.save(update_fields=['is_default'])
        return Response({'message': f'"{template.name}" is now the default offer letter template.'})


# ---------------------------------------------------------------------------
# Router & URL patterns
# ---------------------------------------------------------------------------

messaging_router = DefaultRouter()
messaging_router.register("messages", MessageViewSet, basename="messages")
messaging_router.register("templates", EmailTemplateViewSet, basename="email-templates")
messaging_router.register("offer-templates", OfferLetterTemplateViewSet, basename="offer-letter-templates")

# ---------------------------------------------------------------------------
# Nurture & Campaign ViewSets
# ---------------------------------------------------------------------------

class NurtureSequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurtureSequence
        fields = [
            "id", "name", "description", "is_active",
            "exit_on_reply", "exit_on_apply", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class NurtureSequenceViewSet(viewsets.ModelViewSet):
    serializer_class = NurtureSequenceSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        return NurtureSequence.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, created_by=self.request.user)


class NurtureStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurtureStep
        fields = [
            "id", "sequence", "step_order", "delay_days",
            "channel", "subject", "body", "template", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class NurtureStepViewSet(viewsets.ModelViewSet):
    serializer_class = NurtureStepSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["sequence", "channel"]

    def get_queryset(self):
        return NurtureStep.objects.filter(
            sequence__tenant_id=self.request.tenant_id
        ).select_related("sequence")

    def perform_create(self, serializer):
        serializer.save()


class NurtureEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurtureEnrollment
        fields = [
            "id", "sequence", "candidate", "current_step",
            "status", "exit_reason", "enrolled_at", "next_send_at", "completed_at",
        ]
        read_only_fields = ["id", "enrolled_at"]


class NurtureEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = NurtureEnrollmentSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "sequence", "candidate"]

    def get_queryset(self):
        return NurtureEnrollment.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def exit(self, request, pk=None):
        """Manually exit a candidate from the sequence."""
        enrollment = self.get_object()
        enrollment.status = "exited"
        enrollment.exit_reason = request.data.get("reason", "manual")
        enrollment.save(update_fields=["status", "exit_reason"])
        return Response(NurtureEnrollmentSerializer(enrollment).data)


class CommunicationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationPreferenceCenter
        fields = [
            "id", "candidate",
            "email_job_alerts", "email_application_updates", "email_nurture",
            "sms_interview_reminders", "sms_offers",
            "global_opt_out", "opt_out_at", "updated_at",
        ]
        read_only_fields = ["id", "opt_out_at", "updated_at"]


class CommunicationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = CommunicationPreferenceSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["candidate", "global_opt_out"]

    def get_queryset(self):
        return CommunicationPreferenceCenter.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        from django.utils import timezone
        data = serializer.validated_data
        if data.get("global_opt_out"):
            serializer.save(tenant_id=self.request.tenant_id, opt_out_at=timezone.now())
        else:
            serializer.save(tenant_id=self.request.tenant_id)


class BulkCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkCampaign
        fields = [
            "id", "name", "channel", "template", "subject", "body",
            "segment_query", "recipient_count", "sent_count",
            "open_count", "click_count", "status", "scheduled_for",
            "sent_at", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "sent_count", "open_count", "click_count",
            "sent_at", "created_by", "created_at", "updated_at",
        ]


class BulkCampaignViewSet(viewsets.ModelViewSet):
    serializer_class = BulkCampaignSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "channel"]

    def get_queryset(self):
        return BulkCampaign.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def send_now(self, request, pk=None):
        """Trigger immediate send of a draft campaign."""
        campaign = self.get_object()
        if campaign.status not in ("draft", "scheduled"):
            return Response({"error": "Only draft or scheduled campaigns can be sent"}, status=400)
        campaign.status = "sending"
        campaign.save(update_fields=["status", "updated_at"])
        try:
            from apps.messaging.tasks import send_bulk_campaigns
            send_bulk_campaigns.delay()
        except Exception:
            pass
        return Response(BulkCampaignSerializer(campaign).data)


messaging_router.register("nurture-sequences", NurtureSequenceViewSet, basename="nurture-sequences")
messaging_router.register("nurture-steps", NurtureStepViewSet, basename="nurture-steps")
messaging_router.register("nurture-enrollments", NurtureEnrollmentViewSet, basename="nurture-enrollments")
messaging_router.register("comm-preferences", CommunicationPreferenceViewSet, basename="comm-preferences")
messaging_router.register("bulk-campaigns", BulkCampaignViewSet, basename="bulk-campaigns")

messaging_urlpatterns = [path("", include(messaging_router.urls))]
