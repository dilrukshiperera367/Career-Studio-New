from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Q
from django.utils import timezone
from .models import (
    FeatureFlag, AuditLog, ProviderApprovalQueueItem,
    ReviewModerationAction, CommissionOverride, PlatformAnnouncement,
)
from .serializers import (
    FeatureFlagSerializer, AuditLogSerializer, ProviderApprovalQueueSerializer,
    ReviewModerationActionSerializer, CommissionOverrideSerializer,
    PlatformAnnouncementSerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_staff
        return request.user and request.user.is_staff


class FeatureFlagViewSet(viewsets.ModelViewSet):
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=["get"], url_path="enabled")
    def enabled_flags(self, request):
        flags = FeatureFlag.objects.filter(is_enabled=True)
        serializer = self.get_serializer(flags, many=True)
        return Response(serializer.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = super().get_queryset()
        action_type = self.request.query_params.get("action_type")
        actor = self.request.query_params.get("actor")
        if action_type:
            qs = qs.filter(action_type=action_type)
        if actor:
            qs = qs.filter(actor__email__icontains=actor)
        return qs


class ProviderApprovalQueueViewSet(viewsets.ModelViewSet):
    queryset = ProviderApprovalQueueItem.objects.select_related("provider", "assigned_to").all()
    serializer_class = ProviderApprovalQueueSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = super().get_queryset()
        queue_status = self.request.query_params.get("status")
        if queue_status:
            qs = qs.filter(status=queue_status)
        return qs

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        item = self.get_object()
        item.status = ProviderApprovalQueueItem.QueueStatus.APPROVED
        item.assigned_to = request.user
        item.reviewer_notes = request.data.get("notes", "")
        item.reviewed_at = timezone.now()
        item.save()

        # Approve the underlying provider
        item.provider.status = "approved"
        item.provider.save(update_fields=["status"])

        # Audit log
        AuditLog.objects.create(
            actor=request.user,
            action_type=AuditLog.ActionType.PROVIDER_APPROVED,
            target_model="Provider",
            target_id=str(item.provider.id),
            description=f"Approved via approval queue item {item.id}",
        )
        return Response({"detail": "Provider approved."})

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        item = self.get_object()
        reason = request.data.get("reason", "")
        item.status = ProviderApprovalQueueItem.QueueStatus.REJECTED
        item.assigned_to = request.user
        item.rejection_reason = reason
        item.reviewed_at = timezone.now()
        item.save()

        item.provider.status = "rejected"
        item.provider.save(update_fields=["status"])

        return Response({"detail": "Provider rejected.", "reason": reason})

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        item = self.get_object()
        item.assigned_to = request.user
        item.status = ProviderApprovalQueueItem.QueueStatus.IN_REVIEW
        item.save(update_fields=["assigned_to", "status"])
        return Response({"detail": "Queue item assigned to you."})


class ReviewModerationViewSet(viewsets.ModelViewSet):
    queryset = ReviewModerationAction.objects.select_related("review", "moderator").all()
    serializer_class = ReviewModerationActionSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        action_obj = serializer.save(moderator=self.request.user)
        # Sync moderation status to review
        from apps.reviews.models import Review
        review = action_obj.review
        if action_obj.decision == "approved":
            review.moderation_status = Review.ModerationStatus.APPROVED
        elif action_obj.decision == "rejected":
            review.moderation_status = Review.ModerationStatus.REJECTED
        review.save(update_fields=["moderation_status"])


class CommissionOverrideViewSet(viewsets.ModelViewSet):
    queryset = CommissionOverride.objects.select_related("provider", "approved_by").all()
    serializer_class = CommissionOverrideSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(approved_by=self.request.user)


class PlatformAnnouncementViewSet(viewsets.ModelViewSet):
    queryset = PlatformAnnouncement.objects.all()
    serializer_class = PlatformAnnouncementSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        announcement = self.get_object()
        announcement.is_published = True
        announcement.published_at = timezone.now()
        announcement.save(update_fields=["is_published", "published_at"])
        return Response({"detail": "Announcement published."})

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """
        Returns currently active announcements — visible to any
        authenticated user based on their role.
        """
        now = timezone.now()
        qs = PlatformAnnouncement.objects.filter(
            is_published=True,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
