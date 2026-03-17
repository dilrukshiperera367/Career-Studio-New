"""Job Orders views."""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import JobOrder, JobOrderNote, JobOrderStatusHistory
from .serializers import JobOrderSerializer, JobOrderListSerializer, JobOrderNoteSerializer


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


class JobOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "internal_ref", "client_ref"]
    filterset_fields = ["status", "staffing_type", "priority", "assigned_recruiter", "client_account"]
    ordering_fields = ["created_at", "target_fill_date", "priority"]

    def get_queryset(self):
        return JobOrder.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("assigned_recruiter", "client_account", "account_manager")

    def get_serializer_class(self):
        if self.action == "list":
            return JobOrderListSerializer
        return JobOrderSerializer

    def perform_create(self, serializer):
        from apps.agencies.models import Agency
        agency = Agency.objects.filter(id__in=get_agency_ids(self.request.user)).first()
        serializer.save(agency=agency, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        job_order = self.get_object()
        old_status = job_order.status
        job_order.status = JobOrder.Status.APPROVED
        job_order.approved_by = request.user
        job_order.approved_at = timezone.now()
        job_order.save()
        JobOrderStatusHistory.objects.create(
            job_order=job_order,
            previous_status=old_status,
            new_status=job_order.status,
            changed_by=request.user,
        )
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        original = self.get_object()
        original.pk = None
        original.id = None
        original.status = JobOrder.Status.DRAFT
        original.filled_count = 0
        original.is_clone = True
        original.duplicate_of_id = pk
        original.approved_by = None
        original.approved_at = None
        original.save()
        serializer = JobOrderSerializer(original)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def notes(self, request, pk=None):
        job_order = self.get_object()
        if request.method == "GET":
            notes = job_order.notes_set.all()
            return Response(JobOrderNoteSerializer(notes, many=True).data)
        serializer = JobOrderNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(job_order=job_order, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
