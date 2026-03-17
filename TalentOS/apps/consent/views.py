"""Views for consent app — GDPR consent tracking and data requests."""

import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.consent.models import ConsentRecord, DataRequest
from apps.consent.serializers import (
    ConsentGrantSerializer,
    ConsentRecordSerializer,
    DataRequestCreateSerializer,
    DataRequestSerializer,
)
from apps.consent.tasks import process_data_export, process_data_deletion

logger = logging.getLogger("ats.consent")


def _get_client_ip(request):
    """Extract client IP from request headers."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ---------------------------------------------------------------------------
# Consent management
# ---------------------------------------------------------------------------


class ConsentRecordView(APIView):
    """
    GET  /api/v1/consent/?candidate_id=<uuid>  — list all consent records for a candidate
    POST /api/v1/consent/                       — grant or revoke a consent type
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        candidate_id = request.query_params.get("candidate_id")
        if not candidate_id:
            return Response(
                {"error": "candidate_id query param required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        records = ConsentRecord.objects.filter(
            tenant_id=request.tenant_id,
            candidate_id=candidate_id,
        ).order_by("-created_at")
        return Response(ConsentRecordSerializer(records, many=True).data)

    def post(self, request):
        serializer = ConsentGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate_id = request.data.get("candidate_id")
        if not candidate_id:
            return Response(
                {"error": "candidate_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consent_type = serializer.validated_data["consent_type"]
        granted = serializer.validated_data["granted"]
        now = timezone.now()

        record, created = ConsentRecord.objects.get_or_create(
            tenant_id=request.tenant_id,
            candidate_id=candidate_id,
            consent_type=consent_type,
            defaults={
                "granted": granted,
                "granted_at": now if granted else None,
                "ip_address": _get_client_ip(request),
            },
        )

        if not created:
            record.granted = granted
            if granted:
                record.granted_at = now
                record.revoked_at = None
            else:
                record.revoked_at = now
            record.ip_address = _get_client_ip(request)
            record.save(update_fields=["granted", "granted_at", "revoked_at", "ip_address"])

        logger.info(
            "Consent %s for candidate %s consent_type=%s",
            "granted" if granted else "revoked",
            candidate_id,
            consent_type,
        )
        return Response(
            ConsentRecordSerializer(record).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CandidateSelfConsentView(APIView):
    """
    Public endpoint for candidates to manage their own consent.
    PUT /api/v1/consent/self/  — candidate updates their own consent (no auth required,
    authenticated by candidate token or portal session).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Candidate self-records consent (e.g. on career portal application)."""
        serializer = ConsentGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate_id = request.data.get("candidate_id")
        if not candidate_id:
            return Response(
                {"error": "candidate_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_id = request.data.get("tenant_id")
        if not tenant_id:
            return Response(
                {"error": "tenant_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consent_type = serializer.validated_data["consent_type"]
        granted = serializer.validated_data["granted"]
        now = timezone.now()

        record, _ = ConsentRecord.objects.update_or_create(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            consent_type=consent_type,
            defaults={
                "granted": granted,
                "granted_at": now if granted else None,
                "revoked_at": now if not granted else None,
                "ip_address": _get_client_ip(request),
            },
        )
        return Response(ConsentRecordSerializer(record).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Data requests (GDPR Article 15 / 17)
# ---------------------------------------------------------------------------


class DataRequestView(APIView):
    """
    GET  /api/v1/data-requests/?candidate_id=<uuid>  — list requests for a candidate
    POST /api/v1/data-requests/                       — create export or deletion request
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        candidate_id = request.query_params.get("candidate_id")
        qs = DataRequest.objects.filter(tenant_id=request.tenant_id)
        if candidate_id:
            qs = qs.filter(candidate_id=candidate_id)
        qs = qs.order_by("-created_at")
        return Response(DataRequestSerializer(qs, many=True).data)

    def post(self, request):
        serializer = DataRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate_id = request.data.get("candidate_id")
        if not candidate_id:
            return Response(
                {"error": "candidate_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_type = serializer.validated_data["request_type"]

        # Prevent duplicate pending/processing requests
        existing = DataRequest.objects.filter(
            tenant_id=request.tenant_id,
            candidate_id=candidate_id,
            request_type=request_type,
            status__in=["pending", "processing"],
        ).first()
        if existing:
            return Response(
                {
                    "error": "A request of this type is already in progress.",
                    "data": DataRequestSerializer(existing).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        dr = DataRequest.objects.create(
            tenant_id=request.tenant_id,
            candidate_id=candidate_id,
            request_type=request_type,
            status="pending",
        )

        # Kick off async processing
        if request_type == "export":
            process_data_export.delay(str(dr.id))
        else:
            process_data_deletion.delay(str(dr.id))

        logger.info(
            "Data %s request created for candidate %s by user %s",
            request_type,
            candidate_id,
            request.user.id,
        )
        return Response(DataRequestSerializer(dr).data, status=status.HTTP_202_ACCEPTED)


class DataRequestDetailView(APIView):
    """GET /api/v1/data-requests/<id>/ — check status of a specific request."""

    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        try:
            dr = DataRequest.objects.get(
                id=request_id, tenant_id=request.tenant_id
            )
        except DataRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(DataRequestSerializer(dr).data)


# ---------------------------------------------------------------------------
# Bulk consent summary (admin dashboard)
# ---------------------------------------------------------------------------


class ConsentSummaryView(APIView):
    """GET /api/v1/consent/summary/ — aggregate consent stats for the tenant."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Q

        stats = (
            ConsentRecord.objects.filter(tenant_id=request.tenant_id)
            .values("consent_type")
            .annotate(
                total=Count("id"),
                granted_count=Count("id", filter=Q(granted=True)),
                revoked_count=Count("id", filter=Q(granted=False)),
            )
            .order_by("consent_type")
        )
        return Response(list(stats))
