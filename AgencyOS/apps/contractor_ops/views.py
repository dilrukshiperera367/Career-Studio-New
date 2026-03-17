"""Contractor Ops views."""
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Assignment, AssignmentExtension, ContractorDocument, AssignmentIncident, ContractorCheckIn
from .serializers import (
    AssignmentSerializer, AssignmentListSerializer,
    AssignmentExtensionSerializer, ContractorDocumentSerializer,
    AssignmentIncidentSerializer, ContractorCheckInSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class AssignmentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["candidate__first_name", "candidate__last_name", "worksite_name"]
    filterset_fields = ["status", "assignment_type", "client_account", "assigned_recruiter"]
    ordering_fields = ["start_date", "current_end_date", "created_at"]

    def get_queryset(self):
        return Assignment.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("candidate", "client_account", "assigned_recruiter")

    def get_serializer_class(self):
        if self.action == "list":
            return AssignmentListSerializer
        return AssignmentSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        assignment = self.get_object()
        serializer = AssignmentExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ext = serializer.save(assignment=assignment, requested_by=request.user)
        assignment.extension_count += 1
        if ext.new_end_date:
            assignment.current_end_date = ext.new_end_date
        assignment.status = Assignment.Status.EXTENDED
        assignment.save()
        return Response(AssignmentExtensionSerializer(ext).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = Assignment.Status.ENDED
        assignment.actual_end_date = request.data.get("end_date") or timezone.now().date()
        assignment.save()
        return Response({"status": "ended"})

    @action(detail=True, methods=["get", "post"])
    def documents(self, request, pk=None):
        assignment = self.get_object()
        if request.method == "GET":
            docs = assignment.documents.all()
            return Response(ContractorDocumentSerializer(docs, many=True).data)
        serializer = ContractorDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def incidents(self, request, pk=None):
        assignment = self.get_object()
        if request.method == "GET":
            return Response(AssignmentIncidentSerializer(assignment.incidents.all(), many=True).data)
        serializer = AssignmentIncidentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment, reported_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def check_ins(self, request, pk=None):
        assignment = self.get_object()
        if request.method == "GET":
            return Response(ContractorCheckInSerializer(assignment.check_ins.all(), many=True).data)
        serializer = ContractorCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment, checked_in_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
