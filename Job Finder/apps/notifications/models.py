"""Notifications app — Push / email / SMS notifications, job alerts."""
import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """User notification (multi-channel)."""

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        EMAIL = "email", "Email"
        PUSH = "push", "Push"
        SMS = "sms", "SMS"

    class Category(models.TextChoices):
        APPLICATION = "application", "Application Update"
        JOB_ALERT = "job_alert", "Job Alert"
        MESSAGE = "message", "Message"
        SYSTEM = "system", "System"
        PROMOTION = "promotion", "Promotion"
        REVIEW = "review", "Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    category = models.CharField(max_length=15, choices=Category.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    action_url = models.CharField(max_length=500, blank=True, default="")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"], name="idx_notif_user_read"),
        ]


class NotificationPreference(models.Model):
    """Per-user notification preferences."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    email_application_updates = models.BooleanField(default=True)
    email_job_alerts = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    push_application_updates = models.BooleanField(default=True)
    push_job_alerts = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    sms_application_updates = models.BooleanField(default=False)
    sms_job_alerts = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_notification_preferences"


class JobAlert(models.Model):
    """Saved search criteria for automatic job alerts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_alerts")
    name = models.CharField(max_length=100)
    keywords = models.CharField(max_length=300, blank=True, default="")
    category = models.ForeignKey("taxonomy.JobCategory", on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    job_type = models.CharField(max_length=10, blank=True, default="")
    experience_level = models.CharField(max_length=10, blank=True, default="")
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=[
        ("instant", "Instant"), ("daily", "Daily"), ("weekly", "Weekly"),
    ], default="daily")
    # ── Enhanced alert fields ──
    salary_threshold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                           help_text="Alert when jobs with salary >= this amount are posted")
    work_arrangement = models.CharField(max_length=10, blank=True, default="",
                                         help_text="Filter by work arrangement (remote/onsite/hybrid)")
    company = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="followers_alerts",
                                 help_text="Company-specific alert (new jobs from this company)")
    alert_quality_score = models.FloatField(default=0.0,
                                             help_text="0-100 score based on engagement (open/click/apply rate)")
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_job_alerts"


class AlertEngagementLog(models.Model):
    """Tracks opens, clicks, and applies from alert emails."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert = models.ForeignKey(JobAlert, on_delete=models.CASCADE, related_name="engagement_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sent_at = models.DateTimeField()
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    clicked_job_id = models.UUIDField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_job_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "jf_alert_engagement_logs"
        ordering = ["-sent_at"]
