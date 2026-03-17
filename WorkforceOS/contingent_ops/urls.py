from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VendorViewSet,
    ContingentWorkerViewSet,
    ContingentTimesheetViewSet,
    ContingentComplianceViewSet,
)

router = DefaultRouter()
router.register('contingent/vendors', VendorViewSet, basename='vendors')
router.register('contingent/workers', ContingentWorkerViewSet, basename='contingent-workers')
router.register('contingent/timesheets', ContingentTimesheetViewSet, basename='contingent-timesheets')
router.register('contingent/compliance', ContingentComplianceViewSet, basename='contingent-compliance')

urlpatterns = [
    path('', include(router.urls)),
]
