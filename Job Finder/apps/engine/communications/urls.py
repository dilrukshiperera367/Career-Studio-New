from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.CommunicationTemplateViewSet, basename='comm-template')
router.register(r'messages', views.CommunicationMessageViewSet, basename='comm-message')
router.register(r'preferences', views.CommunicationPreferenceViewSet, basename='comm-preference')

urlpatterns = [
    path('', include(router.urls)),
]
