"""Client Portal views."""
from rest_framework import viewsets, permissions, filters, decorators, response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    ClientPortalAccess, PortalJobOrderRequest, PortalShortlistFeedback,
    SecureMessage, IssueEscalation,
)
from .serializers import (
    ClientPortalAccessSerializer, PortalJobOrderRequestSerializer,
    PortalShortlistFeedbackSerializer, SecureMessageSerializer,
    IssueEscalationSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class ClientPortalAccessViewSet(viewsets.ModelViewSet):
    serializer_class = ClientPortalAccessSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["client", "access_level", "is_active"]

    def get_queryset(self):
        return ClientPortalAccess.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @decorators.action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        access = self.get_object()
        access.is_active = False
        access.save(update_fields=["is_active"])
        return response.Response({"status": "deactivated"})


class PortalJobOrderRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PortalJobOrderRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "client"]
    search_fields = ["job_title"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return PortalJobOrderRequest.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @decorators.action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        req.status = "approved"
        req.save(update_fields=["status"])
        return response.Response({"status": "approved"})

    @decorators.action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        req = self.get_object()
        req.status = "rejected"
        req.save(update_fields=["status"])
        return response.Response({"status": "rejected"})


class PortalShortlistFeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = PortalShortlistFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["shortlist", "decision"]

    def get_queryset(self):
        return PortalShortlistFeedback.objects.filter(
            shortlist__agency_id__in=get_agency_ids(self.request.user)
        )


class SecureMessageViewSet(viewsets.ModelViewSet):
    serializer_class = SecureMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["thread_id", "sender"]
    ordering_fields = ["sent_at"]
    ordering = ["-sent_at"]

    def get_queryset(self):
        return SecureMessage.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user), sender=self.request.user)

    @decorators.action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        msg = self.get_object()
        if not msg.read_at:
            msg.read_at = timezone.now()
            msg.save(update_fields=["read_at"])
        return response.Response({"status": "read"})


class IssueEscalationViewSet(viewsets.ModelViewSet):
    serializer_class = IssueEscalationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["issue_type", "priority", "status"]
    search_fields = ["subject"]
    ordering_fields = ["created_at", "priority"]

    def get_queryset(self):
        return IssueEscalation.objects.filter(agency_id__in=get_agency_ids(self.request.user))

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))

    @decorators.action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        issue = self.get_object()
        issue.status = "resolved"
        issue.resolved_at = timezone.now()
        issue.save(update_fields=["status", "resolved_at"])
        return response.Response({"status": "resolved"})
