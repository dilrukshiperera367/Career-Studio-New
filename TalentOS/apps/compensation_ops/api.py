"""API for Compensation Ops app — salary bands, offer approvals, equity, relocation."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.compensation_ops.models import (
    CompensationBand, OfferApprovalMatrix, OfferApprovalStep,
    EquityGrant, RelocationPackage, CompetitivenessAlert,
    OfferVersion, CounterOfferPlan,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess


# ── Serializers ───────────────────────────────────────────────────────────────

class CompensationBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompensationBand
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class OfferApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferApprovalStep
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class OfferApprovalMatrixSerializer(serializers.ModelSerializer):
    steps = OfferApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = OfferApprovalMatrix
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class EquityGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquityGrant
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class RelocationPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelocationPackage
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class CompetitivenessAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitivenessAlert
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class OfferVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferVersion
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class CounterOfferPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterOfferPlan
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class CompensationBandViewSet(viewsets.ModelViewSet):
    serializer_class = CompensationBandSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["currency", "geo_zone"]
    search_fields = ["name", "geo_zone"]

    def get_queryset(self):
        return CompensationBand.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class OfferApprovalMatrixViewSet(viewsets.ModelViewSet):
    serializer_class = OfferApprovalMatrixSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        return OfferApprovalMatrix.objects.filter(tenant_id=self.request.tenant_id).prefetch_related("steps")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class EquityGrantViewSet(viewsets.ModelViewSet):
    serializer_class = EquityGrantSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["grant_type", "status"]

    def get_queryset(self):
        return EquityGrant.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class RelocationPackageViewSet(viewsets.ModelViewSet):
    serializer_class = RelocationPackageSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["tier", "is_active"]

    def get_queryset(self):
        return RelocationPackage.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class CompetitivenessAlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompetitivenessAlertSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_resolved"]

    def get_queryset(self):
        return CompetitivenessAlert.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.is_resolved = True
        alert.save(update_fields=["is_resolved"])
        return Response(CompetitivenessAlertSerializer(alert).data)


class OfferVersionViewSet(viewsets.ModelViewSet):
    serializer_class = OfferVersionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["application", "status"]

    def get_queryset(self):
        return OfferVersion.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, changed_by=self.request.user)


class CounterOfferPlanViewSet(viewsets.ModelViewSet):
    serializer_class = CounterOfferPlanSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status"]

    def get_queryset(self):
        return CounterOfferPlan.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("bands", CompensationBandViewSet, basename="comp-bands")
router.register("approval-matrices", OfferApprovalMatrixViewSet, basename="offer-approval-matrices")
router.register("equity-grants", EquityGrantViewSet, basename="equity-grants")
router.register("relocation-packages", RelocationPackageViewSet, basename="relocation-packages")
router.register("competitiveness-alerts", CompetitivenessAlertViewSet, basename="comp-alerts")
router.register("offer-versions", OfferVersionViewSet, basename="offer-versions")
router.register("counter-offer-plans", CounterOfferPlanViewSet, basename="counter-offer-plans")

urlpatterns = [path("", include(router.urls))]
