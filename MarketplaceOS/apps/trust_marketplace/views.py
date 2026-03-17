from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone as tz
from .models import ProviderReport, ProviderStrike, Dispute, RiskFlag, QualityScore, BackgroundCheckRecord
from .serializers import (
    ProviderReportSerializer, ProviderStrikeSerializer, DisputeSerializer,
    RiskFlagSerializer, QualityScoreSerializer, BackgroundCheckSerializer,
)


class ProviderReportViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return ProviderReport.objects.all()
        return ProviderReport.objects.filter(reporter=user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        report = self.get_object()
        report.status = ProviderReport.ReportStatus.RESOLVED
        report.resolution_notes = request.data.get("resolution_notes", "")
        report.resolved_at = tz.now()
        report.save(update_fields=["status", "resolution_notes", "resolved_at"])
        return Response(ProviderReportSerializer(report).data)


class DisputeViewSet(viewsets.ModelViewSet):
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "dispute_type"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Dispute.objects.all()
        return Dispute.objects.filter(raised_by=user) | Dispute.objects.filter(booking__provider__user=user)

    def perform_create(self, serializer):
        serializer.save(raised_by=self.request.user)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        outcome = request.data.get("outcome", "resolved_split")
        dispute.status = outcome
        dispute.resolution_notes = request.data.get("resolution_notes", "")
        dispute.resolved_at = tz.now()
        dispute.save()
        return Response(DisputeSerializer(dispute).data)


class QualityScoreViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QualityScoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return QualityScore.objects.all()


class RiskFlagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RiskFlagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return RiskFlag.objects.all()
        return RiskFlag.objects.filter(user=user)


class BackgroundCheckViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BackgroundCheckSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return BackgroundCheckRecord.objects.all()
        return BackgroundCheckRecord.objects.filter(provider__user=user)
