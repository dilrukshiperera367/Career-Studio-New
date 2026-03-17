from rest_framework import generics, permissions
from apps.shared.permissions import IsCampusAdmin
from .models import CrossPlatformSync, LMSIntegration, SISIntegration, SSOConfiguration, WebhookEndpoint
from .serializers import (
    CrossPlatformSyncSerializer,
    LMSIntegrationSerializer,
    SISIntegrationSerializer,
    SSOConfigurationSerializer,
    WebhookEndpointSerializer,
)


def get_campus(request):
    return request.user.campus


class SISIntegrationView(generics.RetrieveUpdateAPIView):
    serializer_class = SISIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_object(self):
        obj, _ = SISIntegration.objects.get_or_create(campus=get_campus(self.request))
        return obj


class LMSIntegrationView(generics.RetrieveUpdateAPIView):
    serializer_class = LMSIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_object(self):
        obj, _ = LMSIntegration.objects.get_or_create(campus=get_campus(self.request))
        return obj


class SSOConfigurationView(generics.RetrieveUpdateAPIView):
    serializer_class = SSOConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_object(self):
        obj, _ = SSOConfiguration.objects.get_or_create(campus=get_campus(self.request))
        return obj


class CrossPlatformSyncListView(generics.ListAPIView):
    serializer_class = CrossPlatformSyncSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_queryset(self):
        return CrossPlatformSync.objects.filter(campus=get_campus(self.request))


class WebhookEndpointListCreateView(generics.ListCreateAPIView):
    serializer_class = WebhookEndpointSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_queryset(self):
        return WebhookEndpoint.objects.filter(campus=get_campus(self.request))

    def perform_create(self, serializer):
        serializer.save(campus=get_campus(self.request))


class WebhookEndpointDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WebhookEndpointSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_queryset(self):
        return WebhookEndpoint.objects.filter(campus=get_campus(self.request))
