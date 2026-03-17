from rest_framework.routers import DefaultRouter
from .views import CommissionPlanViewSet, RecruiterCommissionAssignmentViewSet, CommissionRecordViewSet

router = DefaultRouter()
router.register("plans", CommissionPlanViewSet, basename="commission-plan")
router.register("assignments", RecruiterCommissionAssignmentViewSet, basename="comm-assignment")
router.register("records", CommissionRecordViewSet, basename="commission-record")

urlpatterns = router.urls
