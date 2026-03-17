"""Integrations URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .bridge_views import ATSHireWebhookView, ATSTerminationSyncView

router = DefaultRouter()
router.register(r'connectors', views.IntegrationViewSet, basename='integration')
router.register(r'webhooks', views.WebhookRegistrationViewSet, basename='webhook')

urlpatterns = [
    path('', include(router.urls)),
    path('ats/webhook/', views.ATSWebhookView.as_view(), name='ats-webhook'),
    # ATS → HRM bridge: new hire
    path('ats/hire', ATSHireWebhookView.as_view(), name='ats-hire-webhook'),
    # ATS → HRM bridge: termination sync
    path('ats/terminate', ATSTerminationSyncView.as_view(), name='ats-termination-sync'),
    # HRM → ATS bi-directional: employee termination endpoint
    path('employees/<uuid:employee_id>/terminate/', views.HRMEmployeeTerminateView.as_view(), name='employee-terminate'),
]
