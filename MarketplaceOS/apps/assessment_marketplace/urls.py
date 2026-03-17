from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssessmentVendorViewSet, AssessmentProductViewSet,
    AssessmentOrderViewSet, AssessmentDeliveryViewSet,
    AssessmentResultViewSet,
)

router = DefaultRouter()
router.register(r"assessment-vendors", AssessmentVendorViewSet, basename="assessment-vendor")
router.register(r"assessment-products", AssessmentProductViewSet, basename="assessment-product")
router.register(r"assessment-orders", AssessmentOrderViewSet, basename="assessment-order")
router.register(r"assessment-deliveries", AssessmentDeliveryViewSet, basename="assessment-delivery")
router.register(r"assessment-results", AssessmentResultViewSet, basename="assessment-result")

urlpatterns = [
    path("", include(router.urls)),
]
