from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProviderViewSet, ProviderCredentialViewSet, ProviderAvailabilityViewSet,
    ProviderBlackoutViewSet, ProviderApplicationViewSet,
)

router = DefaultRouter()
router.register("providers", ProviderViewSet, basename="provider")
router.register("provider-credentials", ProviderCredentialViewSet, basename="provider-credential")
router.register("provider-availability", ProviderAvailabilityViewSet, basename="provider-availability")
router.register("provider-blackouts", ProviderBlackoutViewSet, basename="provider-blackout")
router.register("provider-applications", ProviderApplicationViewSet, basename="provider-application")

urlpatterns = [path("", include(router.urls))]
