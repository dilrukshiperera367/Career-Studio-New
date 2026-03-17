from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentTemplateViewSet,
    GeneratedDocumentViewSet,
    PolicyDocumentViewSet,
    PolicyAcknowledgementViewSet,
)

router = DefaultRouter()
router.register('documents/templates', DocumentTemplateViewSet, basename='doc-templates')
router.register('documents/generated', GeneratedDocumentViewSet, basename='generated-docs')
router.register('documents/policies', PolicyDocumentViewSet, basename='policy-docs')
router.register('documents/acknowledgements', PolicyAcknowledgementViewSet, basename='policy-acks')

urlpatterns = [
    path('', include(router.urls)),
]
