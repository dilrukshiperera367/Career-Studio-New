from rest_framework.routers import DefaultRouter
from .views import JobOrderViewSet

router = DefaultRouter()
router.register("", JobOrderViewSet, basename="job-order")

urlpatterns = router.urls
