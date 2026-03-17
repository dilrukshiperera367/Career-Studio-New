from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceCategoryViewSet, ServiceViewSet, ServicePackageViewSet,
    SavedProviderViewSet, SavedServiceViewSet,
)

router = DefaultRouter()
router.register(r"service-categories", ServiceCategoryViewSet, basename="service-category")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"service-packages", ServicePackageViewSet, basename="service-package")
router.register(r"saved-providers", SavedProviderViewSet, basename="catalog-saved-provider")
router.register(r"saved-services", SavedServiceViewSet, basename="catalog-saved-service")

urlpatterns = [
    path("", include(router.urls)),
]
