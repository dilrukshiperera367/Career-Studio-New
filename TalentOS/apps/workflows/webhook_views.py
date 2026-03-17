"""Webhook subscription management views."""
from rest_framework import viewsets, permissions, serializers as drf_serializers
from drf_spectacular.utils import extend_schema
from .models import WebhookSubscription


class WebhookSubscriptionSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = ['id', 'url', 'secret', 'events', 'is_active', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {'secret': {'write_only': True}}


@extend_schema(tags=['Webhooks'])
class WebhookSubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WebhookSubscriptionSerializer

    def get_queryset(self):
        return WebhookSubscription.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)
