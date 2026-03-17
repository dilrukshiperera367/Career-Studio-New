"""API for Vendor Management app — agencies, fee schedules, scorecards, SLAs, submissions."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.vendor_management.models import (
    VendorAgency, VendorContact, VendorAccess, FeeSchedule,
    CandidateOwnershipRule, VendorScorecard, VendorSLA, VendorSubmission,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess


# ── Serializers ───────────────────────────────────────────────────────────────

class VendorAgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorAgency
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class VendorContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContact
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class VendorAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorAccess
        fields = "__all__"
        read_only_fields = ["id", "created_at", "granted_by"]


class FeeScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeSchedule
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class CandidateOwnershipRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateOwnershipRule
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class VendorScorecardSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorScorecard
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class VendorSLASerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorSLA
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class VendorSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorSubmission
        fields = "__all__"
        read_only_fields = ["id", "submitted_at", "reviewed_at", "reviewed_by"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class VendorAgencyViewSet(viewsets.ModelViewSet):
    serializer_class = VendorAgencySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["tier", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return VendorAgency.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class VendorContactViewSet(viewsets.ModelViewSet):
    serializer_class = VendorContactSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["agency", "is_primary"]

    def get_queryset(self):
        return VendorContact.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class VendorAccessViewSet(viewsets.ModelViewSet):
    serializer_class = VendorAccessSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["agency", "access_level"]

    def get_queryset(self):
        return VendorAccess.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            granted_by=self.request.user,
        )


class FeeScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = FeeScheduleSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["agency", "fee_type"]

    def get_queryset(self):
        return FeeSchedule.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class CandidateOwnershipRuleViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateOwnershipRuleSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return CandidateOwnershipRule.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class VendorScorecardViewSet(viewsets.ModelViewSet):
    serializer_class = VendorScorecardSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["agency"]
    ordering_fields = ["period_start", "quality_score"]

    def get_queryset(self):
        return VendorScorecard.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class VendorSLAViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSLASerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["agency", "is_active"]

    def get_queryset(self):
        return VendorSLA.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class VendorSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSubmissionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["agency", "job", "status"]
    ordering_fields = ["submitted_at"]

    def get_queryset(self):
        return VendorSubmission.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("agency", "job")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Accept a vendor submission."""
        from django.utils import timezone
        submission = self.get_object()
        submission.status = "accepted"
        submission.reviewed_at = timezone.now()
        submission.reviewed_by = request.user
        submission.save(update_fields=["status", "reviewed_at", "reviewed_by"])
        return Response(VendorSubmissionSerializer(submission).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a vendor submission with a reason."""
        from django.utils import timezone
        submission = self.get_object()
        submission.status = "rejected"
        submission.rejection_reason = request.data.get("reason", "")
        submission.reviewed_at = timezone.now()
        submission.reviewed_by = request.user
        submission.save(update_fields=[
            "status", "rejection_reason", "reviewed_at", "reviewed_by"
        ])
        return Response(VendorSubmissionSerializer(submission).data)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("agencies", VendorAgencyViewSet, basename="vendor-agencies")
router.register("contacts", VendorContactViewSet, basename="vendor-contacts")
router.register("access", VendorAccessViewSet, basename="vendor-access")
router.register("fee-schedules", FeeScheduleViewSet, basename="fee-schedules")
router.register("ownership-rules", CandidateOwnershipRuleViewSet, basename="ownership-rules")
router.register("scorecards", VendorScorecardViewSet, basename="vendor-scorecards")
router.register("slas", VendorSLAViewSet, basename="vendor-slas")
router.register("submissions", VendorSubmissionViewSet, basename="vendor-submissions")

urlpatterns = [
    path("", include(router.urls)),
]
