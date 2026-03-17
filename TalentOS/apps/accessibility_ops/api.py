"""API for Accessibility Ops app — WCAG 2.2 conformance, accommodation requests, demographic consent."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.accessibility_ops.models import (
    WCAGCriterion,
    AccessibilityReview,
    AccessibilityEvidence,
    AccommodationRequest,
    AccessibilityPreference,
    DemographicDataPermission,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess, IsTenantAdmin


# ── Serializers ───────────────────────────────────────────────────────────────

class WCAGCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WCAGCriterion
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class AccessibilityReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityReview
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class AccessibilityEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityEvidence
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class AccommodationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationRequest
        fields = "__all__"
        read_only_fields = ["id", "tenant", "requested_at", "resolved_at", "updated_at"]


class AccessibilityPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityPreference
        fields = "__all__"
        read_only_fields = ["id", "tenant", "updated_at"]


class DemographicDataPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemographicDataPermission
        fields = "__all__"
        read_only_fields = ["id", "tenant", "consented_at", "withdrawn_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class WCAGCriterionViewSet(viewsets.ModelViewSet):
    """WCAG 2.2 criteria registry — global, not tenant-scoped."""
    serializer_class = WCAGCriterionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["level", "wcag_version"]

    def get_queryset(self):
        return WCAGCriterion.objects.all()


class AccessibilityReviewViewSet(viewsets.ModelViewSet):
    serializer_class = AccessibilityReviewSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["status", "scope"]

    def get_queryset(self):
        return AccessibilityReview.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark an accessibility review as complete."""
        review = self.get_object()
        review.status = "complete"
        review.overall_result = request.data.get("overall_result", review.overall_result)
        review.issues_found = request.data.get("issues_found", review.issues_found)
        review.issues_resolved = request.data.get("issues_resolved", review.issues_resolved)
        review.notes = request.data.get("notes", review.notes)
        review.save(update_fields=["status", "overall_result", "issues_found", "issues_resolved", "notes", "updated_at"])
        return Response(AccessibilityReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def require_remediation(self, request, pk=None):
        """Flag a review as requiring remediation."""
        review = self.get_object()
        review.status = "remediation_required"
        review.save(update_fields=["status", "updated_at"])
        return Response(AccessibilityReviewSerializer(review).data)


class AccessibilityEvidenceViewSet(viewsets.ModelViewSet):
    serializer_class = AccessibilityEvidenceSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["result", "review"]

    def get_queryset(self):
        qs = AccessibilityEvidence.objects.filter(tenant_id=self.request.tenant_id).select_related(
            "criterion", "review"
        )
        review_id = self.kwargs.get("review_pk")
        if review_id:
            qs = qs.filter(review_id=review_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class AccommodationRequestViewSet(viewsets.ModelViewSet):
    serializer_class = AccommodationRequestSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status"]

    def get_queryset(self):
        return AccommodationRequest.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve an accommodation request."""
        from django.utils import timezone
        req = self.get_object()
        req.status = "approved"
        req.approved_accommodation = request.data.get("approved_accommodation", "")
        req.reviewed_by = request.user
        req.resolved_at = timezone.now()
        req.save(update_fields=["status", "approved_accommodation", "reviewed_by", "resolved_at", "updated_at"])
        return Response(AccommodationRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def deny(self, request, pk=None):
        """Deny an accommodation request."""
        from django.utils import timezone
        req = self.get_object()
        req.status = "denied"
        req.denial_reason = request.data.get("denial_reason", "")
        req.reviewed_by = request.user
        req.resolved_at = timezone.now()
        req.save(update_fields=["status", "denial_reason", "reviewed_by", "resolved_at", "updated_at"])
        return Response(AccommodationRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def partially_approve(self, request, pk=None):
        """Partially approve an accommodation with modified terms."""
        from django.utils import timezone
        req = self.get_object()
        req.status = "partially_approved"
        req.approved_accommodation = request.data.get("approved_accommodation", "")
        req.reviewed_by = request.user
        req.resolved_at = timezone.now()
        req.save(update_fields=["status", "approved_accommodation", "reviewed_by", "resolved_at", "updated_at"])
        return Response(AccommodationRequestSerializer(req).data)


class AccessibilityPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = AccessibilityPreferenceSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get_queryset(self):
        return AccessibilityPreference.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class DemographicDataPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = DemographicDataPermissionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]
    filterset_fields = ["is_active", "candidate"]

    def get_queryset(self):
        return DemographicDataPermission.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        """Candidate withdraws demographic data consent (GDPR Art. 7(3))."""
        from django.utils import timezone
        perm = self.get_object()
        perm.is_active = False
        perm.withdrawn_at = timezone.now()
        perm.save(update_fields=["is_active", "withdrawn_at"])
        return Response(DemographicDataPermissionSerializer(perm).data)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("wcag-criteria", WCAGCriterionViewSet, basename="wcag-criteria")
router.register("reviews", AccessibilityReviewViewSet, basename="accessibility-reviews")
router.register("evidence", AccessibilityEvidenceViewSet, basename="accessibility-evidence")
router.register("accommodations", AccommodationRequestViewSet, basename="accommodation-requests")
router.register("preferences", AccessibilityPreferenceViewSet, basename="accessibility-preferences")
router.register("demographic-permissions", DemographicDataPermissionViewSet, basename="demographic-permissions")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "reviews/<uuid:review_pk>/evidence/",
        AccessibilityEvidenceViewSet.as_view({"get": "list", "post": "create"}),
        name="review-evidence-list",
    ),
    path(
        "reviews/<uuid:review_pk>/evidence/<uuid:pk>/",
        AccessibilityEvidenceViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="review-evidence-detail",
    ),
]
