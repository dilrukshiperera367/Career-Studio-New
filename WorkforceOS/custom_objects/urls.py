"""Custom Objects URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'definitions', views.CustomObjectDefinitionViewSet, basename='custom-object-definition')
router.register(r'records', views.CustomObjectRecordViewSet, basename='custom-object-record')

urlpatterns = [path('', include(router.urls))]
