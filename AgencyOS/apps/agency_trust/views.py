"""Agency Trust views."""
from rest_framework import viewsets, permissions, filters, decorators, response
from django_filters.rest_framework import DjangoFilterBackend
from .models import AgencyTrustProfile, AbuseReport, SuspiciousActivityLog, AuditLog
from .serializers import (
    AgencyTrustProfileSerializer, AbuseReportSerializer,
    SuspiciousActivityLogSerializer, AuditLogSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class AgencyTrustProfileViewSet(viewsets.ModelViewSet):
    serializer_class = AgencyTrustProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        return AgencyTrustProfile.objects.filter(agency_id__in=get_agency_ids(self.request.user))


class AbuseReportViewSet(viewsets.ModelViewSet):
    serializer_class = AbuseReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["report_type", "status"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return AbuseReport.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class SuspiciousActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SuspiciousActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["signal_type", "severity"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return SuspiciousActivityLog.objects.filter(agency_id__in=get_agency_ids(self.request.user))


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["actor", "object_type"]
    search_fields = ["action", "object_type"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return AuditLog.objects.filter(agency_id__in=get_agency_ids(self.request.user))
