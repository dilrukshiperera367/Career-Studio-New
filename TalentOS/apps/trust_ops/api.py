"""API for Trust Ops app — Platform integrity, fraud detection, job moderation, safe sharing."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.trust_ops.models import (
    RecruiterVerification,
    EmployerDomainVerification,
    JobModerationQueue,
    SuspiciousSubmission,
    AbuseReport,
    SafeShareLink,
    DocumentScanResult,
    CandidateWatermark,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess, IsTenantAdmin


# ── Serializers ───────────────────────────────────────────────────────────────

class RecruiterVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterVerification
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class EmployerDomainVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerDomainVerification
        fields = "__all__"
        read_only_fields = ["id", "tenant", "dns_token", "last_checked_at", "verified_at", "created_at"]


class JobModerationQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobModerationQueue
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class SuspiciousSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspiciousSubmission
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class AbuseReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbuseReport
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SafeShareLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafeShareLink
        fields = "__all__"
        read_only_fields = ["id", "tenant", "token", "accessed_at", "access_count", "created_at"]


class DocumentScanResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentScanResult
        fields = "__all__"
        read_only_fields = ["id", "tenant", "status", "threat_name", "scanned_at", "created_at"]


class CandidateWatermarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateWatermark
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class RecruiterVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterVerificationSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["status", "verification_method"]

    def get_queryset(self):
        return RecruiterVerification.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """Mark a recruiter as verified."""
        from django.utils import timezone
        record = self.get_object()
        record.status = "verified"
        record.verified_by = request.user
        record.verified_at = timezone.now()
        record.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        return Response(RecruiterVerificationSerializer(record).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Revoke a recruiter verification."""
        record = self.get_object()
        record.status = "revoked"
        record.save(update_fields=["status", "updated_at"])
        return Response(RecruiterVerificationSerializer(record).data)


class EmployerDomainVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = EmployerDomainVerificationSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]

    def get_queryset(self):
        return EmployerDomainVerification.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        import secrets
        token = secrets.token_hex(32)
        serializer.save(tenant_id=self.request.tenant_id, dns_token=token)

    @action(detail=True, methods=["post"])
    def recheck(self, request, pk=None):
        """Trigger a DNS re-check for this domain (queues async task)."""
        from django.utils import timezone
        from apps.trust_ops.tasks import check_employer_domain_dns
        record = self.get_object()
        record.last_checked_at = timezone.now()
        record.save(update_fields=["last_checked_at"])
        check_employer_domain_dns.delay(str(record.id))
        return Response({"queued": True, "domain": record.domain})


class JobModerationQueueViewSet(viewsets.ModelViewSet):
    serializer_class = JobModerationQueueSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["decision", "reason"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return JobModerationQueue.objects.filter(tenant_id=self.request.tenant_id).select_related("job")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a flagged job posting."""
        from django.utils import timezone
        item = self.get_object()
        item.decision = "approved"
        item.reviewed_by = request.user
        item.review_notes = request.data.get("review_notes", "")
        item.reviewed_at = timezone.now()
        item.save(update_fields=["decision", "reviewed_by", "review_notes", "reviewed_at"])
        return Response(JobModerationQueueSerializer(item).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a flagged job posting."""
        from django.utils import timezone
        item = self.get_object()
        item.decision = "rejected"
        item.reviewed_by = request.user
        item.review_notes = request.data.get("review_notes", "")
        item.reviewed_at = timezone.now()
        item.save(update_fields=["decision", "reviewed_by", "review_notes", "reviewed_at"])
        return Response(JobModerationQueueSerializer(item).data)


class SuspiciousSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SuspiciousSubmissionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["status"]

    def get_queryset(self):
        return SuspiciousSubmission.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def clear(self, request, pk=None):
        """Clear a suspicious submission (not fraud)."""
        item = self.get_object()
        item.status = "cleared"
        item.investigated_by = request.user
        item.resolution_notes = request.data.get("resolution_notes", "")
        item.save(update_fields=["status", "investigated_by", "resolution_notes", "updated_at"])
        return Response(SuspiciousSubmissionSerializer(item).data)

    @action(detail=True, methods=["post"])
    def confirm_fraud(self, request, pk=None):
        """Confirm a submission as fraud."""
        item = self.get_object()
        item.status = "confirmed_fraud"
        item.investigated_by = request.user
        item.resolution_notes = request.data.get("resolution_notes", "")
        item.save(update_fields=["status", "investigated_by", "resolution_notes", "updated_at"])
        return Response(SuspiciousSubmissionSerializer(item).data)


class AbuseReportViewSet(viewsets.ModelViewSet):
    serializer_class = AbuseReportSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["status", "report_type"]

    def get_queryset(self):
        return AbuseReport.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark an abuse report as resolved."""
        item = self.get_object()
        item.status = "resolved"
        item.resolution = request.data.get("resolution", "")
        item.assigned_to = request.user
        item.save(update_fields=["status", "resolution", "assigned_to", "updated_at"])
        return Response(AbuseReportSerializer(item).data)


class SafeShareLinkViewSet(viewsets.ModelViewSet):
    serializer_class = SafeShareLinkSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return SafeShareLink.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        import secrets
        token = secrets.token_urlsafe(64)
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
            token=token,
        )


class DocumentScanResultViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentScanResultSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsTenantAdmin]
    filterset_fields = ["status"]

    def get_queryset(self):
        return DocumentScanResult.objects.filter(tenant_id=self.request.tenant_id)


class CandidateWatermarkViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CandidateWatermarkSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return CandidateWatermark.objects.filter(tenant_id=self.request.tenant_id)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("verifications/recruiter", RecruiterVerificationViewSet, basename="recruiter-verifications")
router.register("verifications/domain", EmployerDomainVerificationViewSet, basename="domain-verifications")
router.register("moderation", JobModerationQueueViewSet, basename="job-moderation")
router.register("suspicious", SuspiciousSubmissionViewSet, basename="suspicious-submissions")
router.register("abuse-reports", AbuseReportViewSet, basename="abuse-reports")
router.register("safe-share", SafeShareLinkViewSet, basename="safe-share-links")
router.register("document-scans", DocumentScanResultViewSet, basename="document-scans")
router.register("watermarks", CandidateWatermarkViewSet, basename="candidate-watermarks")

urlpatterns = [
    path("", include(router.urls)),
]
