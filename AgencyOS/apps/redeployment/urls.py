from rest_framework.routers import DefaultRouter
from .views import RedeploymentPoolViewSet, EndingAssignmentAlertViewSet, RedeploymentOpportunityViewSet

router = DefaultRouter()
router.register("pools", RedeploymentPoolViewSet, basename="redeploy-pool")
router.register("alerts", EndingAssignmentAlertViewSet, basename="ending-alert")
router.register("opportunities", RedeploymentOpportunityViewSet, basename="redeploy-opportunity")

urlpatterns = router.urls
