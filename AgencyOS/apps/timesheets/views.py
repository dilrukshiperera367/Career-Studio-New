"""Timesheets views."""
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import TimesheetPeriod, Timesheet, TimesheetEntry, ExpenseReport, ExpenseLineItem
from .serializers import (
    TimesheetPeriodSerializer, TimesheetSerializer, TimesheetListSerializer,
    TimesheetEntrySerializer, ExpenseReportSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class TimesheetPeriodViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["is_locked", "period_type"]
    ordering_fields = ["start_date"]

    def get_queryset(self):
        return TimesheetPeriod.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def get_serializer_class(self):
        return TimesheetPeriodSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        period = self.get_object()
        period.is_locked = True
        period.locked_by = request.user
        period.locked_at = timezone.now()
        period.save()
        return Response({"status": "locked"})


class TimesheetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "assignment", "period"]
    ordering_fields = ["period__start_date", "submitted_at"]

    def get_queryset(self):
        return Timesheet.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("assignment", "period")

    def get_serializer_class(self):
        if self.action == "list":
            return TimesheetListSerializer
        return TimesheetSerializer

    def perform_create(self, serializer):
        ts = serializer.save(agency=get_first_agency(self.request.user))
        ts.compute_totals()
        ts.save()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        ts = self.get_object()
        ts.status = Timesheet.Status.SUBMITTED
        ts.submitted_at = timezone.now()
        ts.save()
        return Response({"status": "submitted"})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        ts = self.get_object()
        approval_type = request.data.get("approval_type", "client")
        if approval_type == "supervisor":
            ts.status = Timesheet.Status.SUPERVISOR_APPROVED
            ts.supervisor_approved_by = request.user
            ts.supervisor_approved_at = timezone.now()
        else:
            ts.status = Timesheet.Status.CLIENT_APPROVED
            ts.client_approved_by = request.user
            ts.client_approved_at = timezone.now()
        ts.save()
        return Response({"status": ts.status})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        ts = self.get_object()
        ts.status = Timesheet.Status.REJECTED
        ts.rejected_by = request.user
        ts.rejection_reason = request.data.get("reason", "")
        ts.save()
        return Response({"status": "rejected"})

    @action(detail=True, methods=["get", "post"])
    def entries(self, request, pk=None):
        ts = self.get_object()
        if request.method == "GET":
            return Response(TimesheetEntrySerializer(ts.entries.all(), many=True).data)
        serializer = TimesheetEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(timesheet=ts)
        ts.compute_totals()
        ts.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExpenseReportViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "assignment", "is_invoiceable"]

    def get_queryset(self):
        return ExpenseReport.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("assignment")

    def get_serializer_class(self):
        return ExpenseReportSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        exp = self.get_object()
        exp.status = ExpenseReport.Status.APPROVED
        exp.approved_by = request.user
        exp.approved_at = timezone.now()
        exp.save()
        return Response({"status": "approved"})
