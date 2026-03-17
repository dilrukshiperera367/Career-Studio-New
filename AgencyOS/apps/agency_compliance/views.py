"""Agency Compliance views."""
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import CompliancePack, ComplianceChecklist, BackgroundCheck, Credential, ConsentLog
from .serializers import (
    CompliancePackSerializer, ComplianceChecklistSerializer,
    BackgroundCheckSerializer, CredentialSerializer, ConsentLogSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class CompliancePackViewSet(viewsets.ModelViewSet):
    serializer_class = CompliancePackSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return CompliancePack.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class ComplianceChecklistViewSet(viewsets.ModelViewSet):
    serializer_class = ComplianceChecklistSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["pack", "is_complete"]

    def get_queryset(self):
        return ComplianceChecklist.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class BackgroundCheckViewSet(viewsets.ModelViewSet):
    serializer_class = BackgroundCheckSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["check_type", "status"]
    search_fields = ["candidate__full_name"]

    def get_queryset(self):
        return BackgroundCheck.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class CredentialViewSet(viewsets.ModelViewSet):
    serializer_class = CredentialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["credential_type", "verified"]
    ordering_fields = ["expiry_date", "created_at"]

    def get_queryset(self):
        return Credential.objects.filter(candidate__agency_id__in=get_agency_ids(self.request.user))


class ConsentLogViewSet(viewsets.ModelViewSet):
    serializer_class = ConsentLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["consent_type"]
    http_method_names = ["get", "post", "head", "options"]  # consent logs are immutable

    def get_queryset(self):
        return ConsentLog.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))
