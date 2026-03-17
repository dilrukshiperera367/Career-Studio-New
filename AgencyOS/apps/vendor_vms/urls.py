from rest_framework.routers import DefaultRouter
from .views import VMSIntegrationViewSet, VMSJobFeedViewSet, VendorScorecardViewSet, SubcontractorPartnerViewSet

router = DefaultRouter()
router.register("integrations", VMSIntegrationViewSet, basename="vms-integration")
router.register("job-feeds", VMSJobFeedViewSet, basename="vms-job-feed")
router.register("scorecards", VendorScorecardViewSet, basename="vendor-scorecard")
router.register("subcontractors", SubcontractorPartnerViewSet, basename="subcontractor")

urlpatterns = router.urls
