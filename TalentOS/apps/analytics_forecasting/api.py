"""API for Analytics Forecasting app — Predictive pipeline analytics, capacity planning, fairness reporting."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.analytics_forecasting.models import (
    FillTimeForecast,
    RecruiterCapacityPlan,
    InterviewerLoadForecast,
    CloseRateForecast,
    FairnessReport,
    PipelineBottleneck,
    ProcessAlert,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess, IsTenantAdmin


# ── Serializers ───────────────────────────────────────────────────────────────

class FillTimeForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = FillTimeForecast
        fields = "__all__"
        read_only_fields = ["id", "tenant", "forecast_date"]


class RecruiterCapacityPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterCapacityPlan
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class InterviewerLoadForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerLoadForecast
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class CloseRateForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloseRateForecast
        fields = "__all__"
        read_only_fields = ["id", "tenant", "forecast_date"]


class FairnessReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FairnessReport
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class PipelineBottleneckSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineBottleneck
        fields = "__all__"
        read_only_fields = ["id", "tenant", "detected_at"]


class ProcessAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessAlert
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class FillTimeForecastViewSet(viewsets.ModelViewSet):
    serializer_class = FillTimeForecastSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job", "human_reviewed"]

    def get_queryset(self):
        return FillTimeForecast.objects.filter(tenant_id=self.request.tenant_id).select_related("job")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def mark_reviewed(self, request, pk=None):
        """EU AI Act Annex III — record that a human has reviewed this forecast."""
        forecast = self.get_object()
        forecast.human_reviewed = True
        forecast.save(update_fields=["human_reviewed"])
        return Response(FillTimeForecastSerializer(forecast).data)


class RecruiterCapacityPlanViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterCapacityPlanSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["recruiter"]

    def get_queryset(self):
        return RecruiterCapacityPlan.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class InterviewerLoadForecastViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewerLoadForecastSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["interviewer", "overloaded"]

    def get_queryset(self):
        return InterviewerLoadForecast.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class CloseRateForecastViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CloseRateForecastSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["application"]

    def get_queryset(self):
        return CloseRateForecast.objects.filter(tenant_id=self.request.tenant_id)


class FairnessReportViewSet(viewsets.ModelViewSet):
    serializer_class = FairnessReportSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["report_type", "job"]

    def get_queryset(self):
        return FairnessReport.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def mark_reviewed(self, request, pk=None):
        """Record that a human has reviewed this fairness report."""
        report = self.get_object()
        report.reviewed_by = request.user
        report.save(update_fields=["reviewed_by"])
        return Response(FairnessReportSerializer(report).data)


class PipelineBottleneckViewSet(viewsets.ModelViewSet):
    serializer_class = PipelineBottleneckSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["severity", "job"]

    def get_queryset(self):
        return PipelineBottleneck.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark a pipeline bottleneck as resolved."""
        from django.utils import timezone
        bottleneck = self.get_object()
        bottleneck.resolved_at = timezone.now()
        bottleneck.save(update_fields=["resolved_at"])
        return Response(PipelineBottleneckSerializer(bottleneck).data)


class ProcessAlertViewSet(viewsets.ModelViewSet):
    serializer_class = ProcessAlertSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["alert_type", "status", "severity"]

    def get_queryset(self):
        return ProcessAlert.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge a process alert."""
        from django.utils import timezone
        alert = self.get_object()
        alert.status = "acknowledged"
        alert.acknowledged_at = timezone.now()
        alert.assigned_to = request.user
        alert.save(update_fields=["status", "acknowledged_at", "assigned_to"])
        return Response(ProcessAlertSerializer(alert).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve a process alert."""
        from django.utils import timezone
        alert = self.get_object()
        alert.status = "resolved"
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["status", "resolved_at"])
        return Response(ProcessAlertSerializer(alert).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        """Dismiss a process alert (no action needed)."""
        alert = self.get_object()
        alert.status = "dismissed"
        alert.save(update_fields=["status"])
        return Response(ProcessAlertSerializer(alert).data)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("fill-time", FillTimeForecastViewSet, basename="fill-time-forecasts")
router.register("recruiter-capacity", RecruiterCapacityPlanViewSet, basename="recruiter-capacity")
router.register("interviewer-load", InterviewerLoadForecastViewSet, basename="interviewer-load")
router.register("close-rate", CloseRateForecastViewSet, basename="close-rate-forecasts")
router.register("fairness-reports", FairnessReportViewSet, basename="fairness-reports")
router.register("bottlenecks", PipelineBottleneckViewSet, basename="pipeline-bottlenecks")
router.register("alerts", ProcessAlertViewSet, basename="process-alerts")

urlpatterns = [
    path("", include(router.urls)),
]
