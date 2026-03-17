"""Redeployment views."""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import RedeploymentPool, RedeploymentPoolMember, EndingAssignmentAlert, RedeploymentOpportunity
from .serializers import (
    RedeploymentPoolSerializer, RedeploymentPoolMemberSerializer,
    EndingAssignmentAlertSerializer, RedeploymentOpportunitySerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class RedeploymentPoolViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["name", "description"]
    filterset_fields = ["pool_type", "is_active"]

    def get_queryset(self):
        return RedeploymentPool.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def get_serializer_class(self):
        return RedeploymentPoolSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @action(detail=True, methods=["get", "post"])
    def members(self, request, pk=None):
        pool = self.get_object()
        if request.method == "GET":
            members = pool.members.filter(status=RedeploymentPoolMember.Status.ACTIVE)
            return Response(RedeploymentPoolMemberSerializer(members, many=True).data)
        serializer = RedeploymentPoolMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(pool=pool, added_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EndingAssignmentAlertViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["alert_status", "assigned_to"]
    ordering_fields = ["assignment_end_date", "days_until_end"]

    def get_queryset(self):
        return EndingAssignmentAlert.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("assignment")

    def get_serializer_class(self):
        return EndingAssignmentAlertSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class RedeploymentOpportunityViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["match_status", "candidate", "job_order"]
    ordering_fields = ["match_score", "created_at"]

    def get_queryset(self):
        return RedeploymentOpportunity.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("candidate", "job_order")

    def get_serializer_class(self):
        return RedeploymentOpportunitySerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))
