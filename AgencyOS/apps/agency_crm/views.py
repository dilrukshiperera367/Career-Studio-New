"""Agency CRM views."""
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import ProspectCompany, ClientAccount, ClientContact, Opportunity, ActivityLog, RateCard, AccountPlan
from .serializers import (
    ProspectCompanySerializer, ClientAccountSerializer, ClientContactSerializer,
    OpportunitySerializer, ActivityLogSerializer, RateCardSerializer, AccountPlanSerializer,
)


def get_agency_ids(user):
    """Return agency IDs the user belongs to."""
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


class CRMViewSetMixin:
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    def get_agency_qs(self, model):
        return model.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        from apps.agencies.models import Agency
        agency_ids = get_agency_ids(self.request.user)
        agency = Agency.objects.filter(id__in=agency_ids).first()
        serializer.save(agency=agency)


class ProspectCompanyViewSet(CRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ProspectCompanySerializer
    search_fields = ["company_name", "industry", "website"]
    filterset_fields = ["stage", "tier", "assigned_to"]
    ordering_fields = ["company_name", "created_at", "stage"]

    def get_queryset(self):
        return self.get_agency_qs(ProspectCompany).select_related("assigned_to")


class ClientAccountViewSet(CRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ClientAccountSerializer
    search_fields = ["company_name", "industry"]
    filterset_fields = ["status", "tier", "deal_type", "is_preferred"]
    ordering_fields = ["company_name", "created_at", "health_score"]

    def get_queryset(self):
        return self.get_agency_qs(ClientAccount).select_related(
            "account_manager", "delivery_manager", "parent_account"
        ).prefetch_related("contacts")


class ClientContactViewSet(CRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ClientContactSerializer
    search_fields = ["first_name", "last_name", "email", "job_title"]
    filterset_fields = ["contact_type", "is_primary", "is_decision_maker", "do_not_contact"]

    def get_queryset(self):
        return self.get_agency_qs(ClientContact).select_related("client_account", "prospect_company")


class OpportunityViewSet(CRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = OpportunitySerializer
    search_fields = ["title"]
    filterset_fields = ["stage", "deal_type", "owner"]
    ordering_fields = ["estimated_value", "expected_close_date", "created_at"]

    def get_queryset(self):
        return self.get_agency_qs(Opportunity).select_related("owner", "client_account", "prospect")


class ActivityLogViewSet(CRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ActivityLogSerializer
    search_fields = ["subject", "body"]
    filterset_fields = ["activity_type", "performed_by"]
    ordering_fields = ["activity_date", "created_at"]

    def get_queryset(self):
        return self.get_agency_qs(ActivityLog).select_related(
            "performed_by", "client_account", "contact"
        )

    def perform_create(self, serializer):
        from apps.agencies.models import Agency
        agency_ids = get_agency_ids(self.request.user)
        agency = Agency.objects.filter(id__in=agency_ids).first()
        serializer.save(agency=agency, performed_by=self.request.user)


class RateCardViewSet(CRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = RateCardSerializer
    search_fields = ["role_title", "level"]
    filterset_fields = ["client_account", "is_active"]

    def get_queryset(self):
        return self.get_agency_qs(RateCard).select_related("client_account")


class AccountPlanViewSet(CRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = AccountPlanSerializer
    filterset_fields = ["client_account"]

    def get_queryset(self):
        return self.get_agency_qs(AccountPlan).select_related("client_account", "owner")
