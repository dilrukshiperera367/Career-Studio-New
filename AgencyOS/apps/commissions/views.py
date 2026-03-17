"""Commissions views."""
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import CommissionPlan, RecruiterCommissionAssignment, CommissionRecord
from .serializers import (
    CommissionPlanSerializer, RecruiterCommissionAssignmentSerializer,
    CommissionRecordSerializer, CommissionRecordListSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class CommissionPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["name"]
    filterset_fields = ["plan_type", "commission_model", "is_active"]

    def get_queryset(self):
        return CommissionPlan.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def get_serializer_class(self):
        return CommissionPlanSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class RecruiterCommissionAssignmentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["recruiter", "plan", "is_active"]

    def get_queryset(self):
        return RecruiterCommissionAssignment.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("recruiter", "plan")

    def get_serializer_class(self):
        return RecruiterCommissionAssignmentSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))


class CommissionRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "commission_type", "recruiter"]
    ordering_fields = ["created_at", "gross_commission", "recruiter_amount"]

    def get_queryset(self):
        return CommissionRecord.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("recruiter", "am_user", "plan")

    def get_serializer_class(self):
        if self.action == "list":
            return CommissionRecordListSerializer
        return CommissionRecordSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        record = self.get_object()
        record.status = CommissionRecord.Status.APPROVED
        record.approved_by = request.user
        record.approved_at = timezone.now()
        record.save()
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        record = self.get_object()
        record.status = CommissionRecord.Status.PAID
        record.paid_at = timezone.now()
        record.payment_reference = request.data.get("reference", "")
        record.save()
        return Response({"status": "paid"})
