"""Mobile API — serializers."""
from rest_framework import serializers
from .models import PushDeviceToken, DevicePreference, MobileSessionLog


class PushDeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDeviceToken
        fields = ["id", "token", "platform", "device_id", "app_version",
                  "os_version", "is_active", "registered_at"]
        read_only_fields = ["id", "registered_at", "is_active"]


class DevicePreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevicePreference
        fields = ["device_id", "language", "enable_job_alerts", "enable_application_updates",
                  "enable_messages", "enable_promotions", "commute_location_lat",
                  "commute_location_lng", "commute_radius_km", "low_bandwidth_mode"]
