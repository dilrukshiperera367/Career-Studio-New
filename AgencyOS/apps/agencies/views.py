from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from .models import (
    Agency, AgencyClient, AgencyRecruiter, AgencyJobOrder,
    AgencySubmission, AgencyPlacement, AgencyContractor, TalentPool,
)
from .serializers import (
    AgencySerializer, AgencyClientSerializer, AgencyRecruiterSerializer,
    AgencyJobOrderSerializer, AgencySubmissionSerializer,
    AgencyPlacementSerializer, AgencyContractorSerializer, TalentPoolSerializer,
)


class AgencyViewSet(viewsets.ModelViewSet):
    queryset = Agency.objects.all()
    serializer_class = AgencySerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "description"]
    filterset_fields = ["tier", "is_verified", "country"]
    ordering_fields = ["name", "created_at", "total_placements"]

    def get_queryset(self):
        return Agency.objects.filter(
            Q(owner=self.request.user) |
            Q(recruiters__user=self.request.user)
        ).distinct()

    @action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        """Agency dashboard KPIs."""
        agency = self.get_object()
        data = {
            "active_clients": agency.clients.filter(status="active").count(),
            "open_job_orders": agency.job_orders.filter(status="open").count(),
            "total_submissions": agency.submissions.count(),
            "pending_submissions": agency.submissions.filter(status="submitted").count(),
            "total_placements": agency.placements_via_submissions.filter(is_active=True).count() if hasattr(agency, 'placements_via_submissions') else 0,
            "available_contractors": agency.contractors.filter(status="available").count(),
        }
        return Response(data)


class AgencyClientViewSet(viewsets.ModelViewSet):
    serializer_class = AgencyClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["agency", "status", "fee_type"]
    search_fields = ["employer_name", "employer_contact_email"]
    ordering_fields = ["employer_name", "created_at"]

    def get_queryset(self):
        return AgencyClient.objects.filter(
            agency__recruiters__user=self.request.user
        ).select_related("agency").distinct()


class AgencyRecruiterViewSet(viewsets.ModelViewSet):
    serializer_class = AgencyRecruiterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["agency", "role", "is_active"]
    search_fields = ["user__email", "desk"]

    def get_queryset(self):
        return AgencyRecruiter.objects.filter(
            agency__recruiters__user=self.request.user
        ).select_related("agency", "user").distinct()


class AgencyJobOrderViewSet(viewsets.ModelViewSet):
    serializer_class = AgencyJobOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["agency", "client", "status", "priority", "employment_type"]
    search_fields = ["title", "description", "required_skills"]
    ordering_fields = ["created_at", "target_fill_date", "priority"]

    def get_queryset(self):
        return AgencyJobOrder.objects.filter(
            agency__recruiters__user=self.request.user
        ).select_related("agency", "client", "assigned_recruiter").distinct()


class AgencySubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = AgencySubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["agency", "client", "status", "job_order"]
    search_fields = ["candidate_name", "candidate_email"]
    ordering_fields = ["created_at", "ownership_start"]

    def get_queryset(self):
        return AgencySubmission.objects.filter(
            agency__recruiters__user=self.request.user
        ).select_related("agency", "client", "job_order", "recruiter").distinct()

    @action(detail=True, methods=["post"])
    def advance_status(self, request, pk=None):
        """Advance submission to next stage."""
        submission = self.get_object()
        status_order = [
            "submitted", "reviewed", "shortlisted",
            "interview", "offer", "placed"
        ]
        current_idx = status_order.index(submission.status) if submission.status in status_order else -1
        if current_idx < len(status_order) - 1:
            submission.status = status_order[current_idx + 1]
            submission.save()
        return Response(AgencySubmissionSerializer(submission).data)


class AgencyPlacementViewSet(viewsets.ModelViewSet):
    serializer_class = AgencyPlacementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["placement_type", "is_active", "fee_paid"]
    ordering_fields = ["start_date", "fee_amount", "created_at"]

    def get_queryset(self):
        return AgencyPlacement.objects.filter(
            submission__agency__recruiters__user=self.request.user
        ).select_related("submission").distinct()


class AgencyContractorViewSet(viewsets.ModelViewSet):
    serializer_class = AgencyContractorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["agency", "status"]
    search_fields = ["person__email", "skills"]
    ordering_fields = ["created_at", "assignment_end"]

    def get_queryset(self):
        return AgencyContractor.objects.filter(
            agency__recruiters__user=self.request.user
        ).select_related("agency", "person", "current_client").distinct()

    @action(detail=True, methods=["post"])
    def redeploy(self, request, pk=None):
        """Move contractor to a different client assignment."""
        contractor = self.get_object()
        new_client_id = request.data.get("client_id")
        if new_client_id:
            try:
                new_client = AgencyClient.objects.get(id=new_client_id)
                contractor.current_client = new_client
                contractor.status = "on_assignment"
                contractor.extension_count += 1
                contractor.save()
            except AgencyClient.DoesNotExist:
                return Response({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AgencyContractorSerializer(contractor).data)


class TalentPoolViewSet(viewsets.ModelViewSet):
    serializer_class = TalentPoolSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["agency", "is_active"]
    search_fields = ["name", "description", "tags"]

    def get_queryset(self):
        return TalentPool.objects.filter(
            agency__recruiters__user=self.request.user
        ).prefetch_related("members").distinct()
