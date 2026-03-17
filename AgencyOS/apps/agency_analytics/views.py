"""Agency Analytics views."""
from rest_framework import viewsets, permissions, filters, decorators, response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import DailyKPISnapshot, RecruiterPerformance, ClientAnalytics, FunnelMetrics
from .serializers import (
    DailyKPISnapshotSerializer, RecruiterPerformanceSerializer,
    ClientAnalyticsSerializer, FunnelMetricsSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


class DailyKPISnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyKPISnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["snapshot_date"]
    ordering_fields = ["snapshot_date"]
    ordering = ["-snapshot_date"]

    def get_queryset(self):
        return DailyKPISnapshot.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    @decorators.action(detail=False, methods=["get"])
    def today(self, request):
        today = timezone.now().date()
        snapshot = self.get_queryset().filter(snapshot_date=today).first()
        if not snapshot:
            return response.Response({})
        return response.Response(DailyKPISnapshotSerializer(snapshot).data)


class RecruiterPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecruiterPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["recruiter", "period_start", "period_end"]
    ordering_fields = ["period_start", "placements_made", "revenue_generated"]

    def get_queryset(self):
        return RecruiterPerformance.objects.filter(agency_id__in=get_agency_ids(self.request.user))


class ClientAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClientAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["client"]
    ordering_fields = ["period_start", "revenue_generated"]

    def get_queryset(self):
        return ClientAnalytics.objects.filter(agency_id__in=get_agency_ids(self.request.user))


class FunnelMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FunnelMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["period_start", "period_end", "job_order"]
    ordering_fields = ["period_start"]

    def get_queryset(self):
        return FunnelMetrics.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    @decorators.action(detail=False, methods=["get"])
    def summary(self, request):
        from django.db.models import Avg, Sum
        qs = self.get_queryset()
        agg = qs.aggregate(
            avg_sourced=Avg("sourced"),
            avg_submitted=Avg("submitted"),
            avg_placed=Avg("placed"),
            total_placed=Sum("placed"),
        )
        return response.Response(agg)
