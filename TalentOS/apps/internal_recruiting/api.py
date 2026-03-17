"""API for Internal Recruiting app — Internal mobility, transfers, and manager approvals."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.internal_recruiting.models import (
    InternalPostingWindow,
    InternalRequisition,
    InternalApplication,
    InternalTransferRequest,
    ManagerApproval,
    InternalVsExternalComparison,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess, IsTenantAdmin


# ── Serializers ───────────────────────────────────────────────────────────────

class InternalPostingWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalPostingWindow
        fields = "__all__"
        read_only_fields = ["id", "tenant", "notification_sent_at", "created_at"]


class InternalRequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalRequisition
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class InternalApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalApplication
        fields = "__all__"
        read_only_fields = ["id", "tenant", "applied_at", "updated_at"]


class InternalTransferRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalTransferRequest
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class ManagerApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerApproval
        fields = "__all__"
        read_only_fields = ["id", "tenant", "decided_at", "created_at"]


class InternalVsExternalComparisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalVsExternalComparison
        fields = "__all__"
        read_only_fields = ["id", "tenant", "snapshot_date"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class InternalPostingWindowViewSet(viewsets.ModelViewSet):
    serializer_class = InternalPostingWindowSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return InternalPostingWindow.objects.filter(tenant_id=self.request.tenant_id).select_related("job")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def notify_employees(self, request, pk=None):
        """Send internal job posting notification to all employees."""
        from django.utils import timezone
        from apps.internal_recruiting.tasks import notify_employees_of_internal_postings
        window = self.get_object()
        notify_employees_of_internal_postings.delay(str(window.id))
        window.notification_sent_at = timezone.now()
        window.save(update_fields=["notification_sent_at"])
        return Response({"queued": True})


class InternalRequisitionViewSet(viewsets.ModelViewSet):
    serializer_class = InternalRequisitionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "department"]

    def get_queryset(self):
        return InternalRequisition.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        """Open an internal requisition for applications."""
        req = self.get_object()
        req.status = "open"
        req.save(update_fields=["status", "updated_at"])
        return Response(InternalRequisitionSerializer(req).data)

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        """Mark an internal requisition as filled."""
        req = self.get_object()
        req.status = "filled"
        req.save(update_fields=["status", "updated_at"])
        return Response(InternalRequisitionSerializer(req).data)


class InternalApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = InternalApplicationSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "requisition"]

    def get_queryset(self):
        return InternalApplication.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            applicant=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def shortlist(self, request, pk=None):
        """Move an internal application to shortlisted."""
        app = self.get_object()
        app.status = "shortlisted"
        app.save(update_fields=["status", "updated_at"])
        return Response(InternalApplicationSerializer(app).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject an internal application."""
        app = self.get_object()
        app.status = "rejected"
        app.notes = request.data.get("notes", app.notes)
        app.save(update_fields=["status", "notes", "updated_at"])
        return Response(InternalApplicationSerializer(app).data)


class InternalTransferRequestViewSet(viewsets.ModelViewSet):
    serializer_class = InternalTransferRequestSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "transfer_type"]

    def get_queryset(self):
        return InternalTransferRequest.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            initiated_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a transfer request."""
        transfer = self.get_object()
        transfer.status = "approved"
        transfer.save(update_fields=["status", "updated_at"])
        return Response(InternalTransferRequestSerializer(transfer).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a transfer request."""
        transfer = self.get_object()
        transfer.status = "rejected"
        transfer.reason = request.data.get("reason", transfer.reason)
        transfer.save(update_fields=["status", "reason", "updated_at"])
        return Response(InternalTransferRequestSerializer(transfer).data)


class ManagerApprovalViewSet(viewsets.ModelViewSet):
    serializer_class = ManagerApprovalSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["decision"]

    def get_queryset(self):
        return ManagerApproval.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            manager=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        """Record a manager's approval decision."""
        from django.utils import timezone
        approval = self.get_object()
        decision = request.data.get("decision")
        if decision not in ("approved", "denied", "conditionally_approved"):
            return Response(
                {"error": "decision must be approved, denied, or conditionally_approved"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        approval.decision = decision
        approval.notes = request.data.get("notes", approval.notes)
        approval.decided_at = timezone.now()
        approval.save(update_fields=["decision", "notes", "decided_at"])
        return Response(ManagerApprovalSerializer(approval).data)


class InternalVsExternalComparisonViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InternalVsExternalComparisonSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job"]

    def get_queryset(self):
        return InternalVsExternalComparison.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related("job")


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("posting-windows", InternalPostingWindowViewSet, basename="internal-posting-windows")
router.register("requisitions", InternalRequisitionViewSet, basename="internal-requisitions")
router.register("applications", InternalApplicationViewSet, basename="internal-applications")
router.register("transfers", InternalTransferRequestViewSet, basename="internal-transfers")
router.register("manager-approvals", ManagerApprovalViewSet, basename="manager-approvals")
router.register("comparisons", InternalVsExternalComparisonViewSet, basename="internal-vs-external")

urlpatterns = [
    path("", include(router.urls)),
]
