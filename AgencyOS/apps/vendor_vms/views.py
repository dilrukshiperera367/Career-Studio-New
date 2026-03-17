"""Vendor / VMS views."""
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import VMSIntegration, VMSJobFeed, VendorScorecard, SubcontractorPartner
from .serializers import (
    VMSIntegrationSerializer, VMSJobFeedSerializer,
    VendorScorecardSerializer, SubcontractorPartnerSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class VMSIntegrationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["platform", "status", "is_msp_managed"]

    def get_queryset(self):
        return VMSIntegration.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def get_serializer_class(self):
        return VMSIntegrationSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class VMSJobFeedViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["title", "vms_job_id"]
    filterset_fields = ["status", "integration"]

    def get_queryset(self):
        return VMSJobFeed.objects.filter(
            integration__agency_id__in=get_agency_ids(self.request.user)
        ).select_related("integration", "job_order")

    def get_serializer_class(self):
        return VMSJobFeedSerializer


class VendorScorecardViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["integration"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return VendorScorecard.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("integration")

    def get_serializer_class(self):
        return VendorScorecardSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class SubcontractorPartnerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["partner_name", "contact_name"]
    filterset_fields = ["status", "insurance_verified", "compliance_verified"]

    def get_queryset(self):
        return SubcontractorPartner.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def get_serializer_class(self):
        return SubcontractorPartnerSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))
