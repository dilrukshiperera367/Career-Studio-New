from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AIModelViewSet,
    AIDecisionLogViewSet,
    PrivacyConsentViewSet,
    DataRetentionPolicyViewSet,
    AccessibilityConfigViewSet,
)

router = DefaultRouter()
router.register('compliance/ai-models', AIModelViewSet, basename='ai-models')
router.register('compliance/ai-decisions', AIDecisionLogViewSet, basename='ai-decisions')
router.register('compliance/privacy-consents', PrivacyConsentViewSet, basename='privacy-consents')
router.register('compliance/data-retention', DataRetentionPolicyViewSet, basename='data-retention')
router.register('compliance/accessibility', AccessibilityConfigViewSet, basename='accessibility-config')

urlpatterns = [
    path('', include(router.urls)),
]
