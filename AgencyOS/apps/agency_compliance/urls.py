"""Agency Compliance URL configuration."""
from rest_framework.routers import DefaultRouter
from .views import (
    CompliancePackViewSet, ComplianceChecklistViewSet,
    BackgroundCheckViewSet, CredentialViewSet, ConsentLogViewSet,
)

router = DefaultRouter()
router.register("packs", CompliancePackViewSet, basename="compliance-pack")
router.register("checklists", ComplianceChecklistViewSet, basename="compliance-checklist")
router.register("background-checks", BackgroundCheckViewSet, basename="background-check")
router.register("credentials", CredentialViewSet, basename="credential")
router.register("consent-logs", ConsentLogViewSet, basename="consent-log")

urlpatterns = router.urls
