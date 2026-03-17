from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FeatureFlagViewSet, AuditLogViewSet, ProviderApprovalQueueViewSet,
    ReviewModerationViewSet, CommissionOverrideViewSet, PlatformAnnouncementViewSet,
)

router = DefaultRouter()
router.register(r"feature-flags", FeatureFlagViewSet, basename="feature-flag")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")
router.register(r"provider-approval-queue", ProviderApprovalQueueViewSet, basename="provider-approval-queue")
router.register(r"review-moderation", ReviewModerationViewSet, basename="review-moderation")
router.register(r"commission-overrides", CommissionOverrideViewSet, basename="commission-override")
router.register(r"announcements", PlatformAnnouncementViewSet, basename="announcement")

urlpatterns = [
    path("", include(router.urls)),
]
