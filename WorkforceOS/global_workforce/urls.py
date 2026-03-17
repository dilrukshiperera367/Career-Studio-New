from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CountryPackViewSet,
    ExpatAssignmentViewSet,
    VisaPermitViewSet,
    MultiCurrencyRateViewSet,
)

router = DefaultRouter()
router.register('global/country-packs', CountryPackViewSet, basename='country-packs')
router.register('global/expat', ExpatAssignmentViewSet, basename='expat-assignments')
router.register('global/visas', VisaPermitViewSet, basename='visa-permits')
router.register('global/currency-rates', MultiCurrencyRateViewSet, basename='currency-rates')

urlpatterns = [
    path('', include(router.urls)),
]
