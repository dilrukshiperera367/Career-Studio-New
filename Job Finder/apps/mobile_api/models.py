"""Mobile API — push tokens, device preferences, mobile analytics."""
import uuid
from django.db import models
from django.conf import settings


class PushDeviceToken(models.Model):
    """FCM/APNs push notification token per device."""
    class Platform(models.TextChoices):
        FCM = "fcm", "Firebase (Android)"
        APNS = "apns", "Apple (iOS)"
        WEB = "web", "Web Push"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="mobile_push_tokens")
    token = models.TextField(unique=True, help_text="FCM registration token or APNs device token")
    platform = models.CharField(max_length=5, choices=Platform.choices)
    device_id = models.CharField(max_length=200, blank=True, default="")
    app_version = models.CharField(max_length=20, blank=True, default="")
    os_version = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jf_push_device_tokens"
        ordering = ["-registered_at"]
        indexes = [
            models.Index(fields=["user", "is_active"], name="idx_push_user_active"),
        ]

    def __str__(self):
        return f"PushToken: {self.user} [{self.platform}]"


class DevicePreference(models.Model):
    """Device-level app and notification preferences."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="device_preferences")
    device_id = models.CharField(max_length=200)
    language = models.CharField(max_length=5, default="en")
    enable_job_alerts = models.BooleanField(default=True)
    enable_application_updates = models.BooleanField(default=True)
    enable_messages = models.BooleanField(default=True)
    enable_promotions = models.BooleanField(default=False)
    commute_location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    commute_location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    commute_radius_km = models.IntegerField(default=25)
    low_bandwidth_mode = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_device_preferences"
        unique_together = ["user", "device_id"]

    def __str__(self):
        return f"DevicePref: {self.user} [{self.device_id[:20]}]"


class MobileSessionLog(models.Model):
    """Mobile session analytics — app opens, screens visited."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    device_id = models.CharField(max_length=200, blank=True, default="")
    platform = models.CharField(max_length=5)
    app_version = models.CharField(max_length=20, blank=True, default="")
    screens_visited = models.JSONField(default=list)
    jobs_viewed = models.JSONField(default=list)
    session_duration_seconds = models.IntegerField(default=0)
    session_start = models.DateTimeField()
    session_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_mobile_session_logs"
        ordering = ["-session_start"]
