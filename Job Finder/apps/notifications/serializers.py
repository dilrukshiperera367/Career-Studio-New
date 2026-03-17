"""Notifications serializers."""
from rest_framework import serializers
from .models import Notification, NotificationPreference, JobAlert


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "channel", "category", "title", "body", "data",
            "action_url", "is_read", "read_at", "created_at",
        ]
        read_only_fields = ["id", "channel", "category", "title", "body", "data", "action_url", "created_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "email_application_updates", "email_job_alerts",
            "email_messages", "email_marketing",
            "push_application_updates", "push_job_alerts", "push_messages",
            "sms_application_updates", "sms_job_alerts",
        ]


class JobAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAlert
        fields = [
            "id", "name", "keywords", "category", "district",
            "job_type", "experience_level", "salary_min",
            "frequency", "is_active", "last_sent_at", "created_at",
        ]
        read_only_fields = ["id", "last_sent_at", "created_at"]
