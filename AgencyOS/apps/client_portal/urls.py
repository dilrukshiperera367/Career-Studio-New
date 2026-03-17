"""Client Portal URL configuration."""
from rest_framework.routers import DefaultRouter
from .views import (
    ClientPortalAccessViewSet, PortalJobOrderRequestViewSet,
    PortalShortlistFeedbackViewSet, SecureMessageViewSet, IssueEscalationViewSet,
)

router = DefaultRouter()
router.register("access", ClientPortalAccessViewSet, basename="portal-access")
router.register("job-requests", PortalJobOrderRequestViewSet, basename="portal-job-request")
router.register("shortlist-feedback", PortalShortlistFeedbackViewSet, basename="portal-shortlist-feedback")
router.register("messages", SecureMessageViewSet, basename="portal-message")
router.register("escalations", IssueEscalationViewSet, basename="portal-escalation")

urlpatterns = router.urls
