"""Agency Trust URL configuration."""
from rest_framework.routers import DefaultRouter
from .views import (
    AgencyTrustProfileViewSet, AbuseReportViewSet,
    SuspiciousActivityLogViewSet, AuditLogViewSet,
)

router = DefaultRouter()
router.register("profiles", AgencyTrustProfileViewSet, basename="trust-profile")
router.register("abuse-reports", AbuseReportViewSet, basename="abuse-report")
router.register("suspicious-activity", SuspiciousActivityLogViewSet, basename="suspicious-activity")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = router.urls
