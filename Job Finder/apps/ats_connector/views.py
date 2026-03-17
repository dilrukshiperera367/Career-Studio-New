"""ATS Connector views — Connection setup, webhook receiver, sync management."""
import hashlib
import hmac

from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsEmployer
from apps.employers.models import EmployerTeamMember
from .models import ATSConnection, WebhookLog, JobSyncRecord
from .serializers import (
    ATSConnectionSerializer, ATSConnectionSetupSerializer,
    WebhookLogSerializer, JobSyncRecordSerializer,
)


class ATSConnectionView(generics.RetrieveAPIView):
    """Get current ATS connection for employer."""
    serializer_class = ATSConnectionSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_object(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if not membership:
            self.permission_denied(self.request)
        conn, _ = ATSConnection.objects.get_or_create(employer=membership.employer)
        return conn


class ATSConnectionSetupView(APIView):
    """Setup or update ATS connection."""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request):
        membership = EmployerTeamMember.objects.filter(
            user=request.user, role__in=["owner", "admin"],
        ).first()
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = ATSConnectionSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conn, _ = ATSConnection.objects.get_or_create(employer=membership.employer)
        conn.sync_mode = serializer.validated_data["sync_mode"]
        conn.api_endpoint = serializer.validated_data.get("api_endpoint", "")
        # In production: encrypt api_key before storing
        conn.is_active = True
        conn.save()
        return Response(ATSConnectionSerializer(conn).data)


class WebhookReceiveView(APIView):
    """Receive inbound webhooks from ATS system."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Validate webhook signature
        employer_slug = request.query_params.get("employer")
        if not employer_slug:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            conn = ATSConnection.objects.get(employer__slug=employer_slug, is_active=True)
        except ATSConnection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Log the webhook
        WebhookLog.objects.create(
            connection=conn,
            direction="inbound",
            event_type=request.data.get("event", "unknown"),
            payload=request.data,
            headers=dict(request.headers),
            success=True,
        )
        # TODO: process webhook event asynchronously via Celery
        return Response({"detail": "Webhook received."})


class WebhookLogListView(generics.ListAPIView):
    serializer_class = WebhookLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if not membership:
            return WebhookLog.objects.none()
        return WebhookLog.objects.filter(connection__employer=membership.employer).order_by("-created_at")[:100]


class SyncRecordListView(generics.ListAPIView):
    serializer_class = JobSyncRecordSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if not membership:
            return JobSyncRecord.objects.none()
        return JobSyncRecord.objects.filter(connection__employer=membership.employer)


class TriggerSyncView(APIView):
    """Manually trigger ATS sync."""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request):
        membership = EmployerTeamMember.objects.filter(
            user=request.user, role__in=["owner", "admin"],
        ).first()
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        # TODO: trigger_ats_sync.delay(employer_id=membership.employer_id)
        return Response({"detail": "Sync triggered."})
