from rest_framework import serializers
from .models import CrossPlatformSync, LMSIntegration, SISIntegration, SSOConfiguration, WebhookEndpoint


class SISIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SISIntegration
        exclude = ["api_key_hint"]
        read_only_fields = ["id", "campus", "last_sync_at", "last_sync_status", "sync_log"]


class LMSIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LMSIntegration
        exclude = ["api_key_hint"]
        read_only_fields = ["id", "campus", "last_sync_at"]


class SSOConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SSOConfiguration
        exclude = ["idp_cert_hint"]
        read_only_fields = ["id", "campus"]


class CrossPlatformSyncSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossPlatformSync
        fields = "__all__"
        read_only_fields = ["id", "campus", "last_synced_at", "status", "error_message"]


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        exclude = ["secret_hint"]
        read_only_fields = ["id", "campus", "failure_count", "last_triggered_at", "last_status_code"]
