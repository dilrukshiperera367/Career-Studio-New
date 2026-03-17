from django.urls import path
from . import views

urlpatterns = [
    path("sis/", views.SISIntegrationView.as_view(), name="sis-integration"),
    path("lms/", views.LMSIntegrationView.as_view(), name="lms-integration"),
    path("sso/", views.SSOConfigurationView.as_view(), name="sso-config"),
    path("syncs/", views.CrossPlatformSyncListView.as_view(), name="cross-platform-syncs"),
    path("webhooks/", views.WebhookEndpointListCreateView.as_view(), name="webhooks"),
    path("webhooks/<uuid:pk>/", views.WebhookEndpointDetailView.as_view(), name="webhook-detail"),
]
