"""Retention & Growth — reactivation campaigns, inactivity tracking, digest queues."""
import uuid
from django.db import models
from django.conf import settings


class RetentionCampaign(models.Model):
    """System or admin-defined retention campaign for seekers."""
    class CampaignType(models.TextChoices):
        INACTIVITY_REACTIVATION = "reactivation", "Inactivity Reactivation"
        WEEKLY_DIGEST = "weekly_digest", "Weekly Job Digest"
        MISSED_OPPORTUNITY = "missed_opportunity", "Missed Opportunity Alert"
        NEW_SINCE_LAST_VISIT = "new_since_visit", "New Since Last Visit"
        PROFILE_INCOMPLETE = "profile_incomplete", "Complete Your Profile"
        SAVED_JOB_EXPIRING = "saved_expiring", "Saved Job Expiring Soon"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    campaign_type = models.CharField(max_length=25, choices=CampaignType.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    subject_template = models.CharField(max_length=300, blank=True, default="")
    body_template = models.TextField(blank=True, default="")
    inactivity_threshold_days = models.IntegerField(default=7,
                                                     help_text="Days of inactivity to trigger (for reactivation)")
    audience_filter = models.JSONField(default=dict, help_text="JSON filter criteria for targeted audience")
    target_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    reactivation_count = models.IntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_retention_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"RetCampaign: {self.name} ({self.campaign_type})"


class InactivityRecord(models.Model):
    """Tracks user inactivity windows for reactivation logic."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="inactivity_record")
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_search_at = models.DateTimeField(null=True, blank=True)
    last_application_at = models.DateTimeField(null=True, blank=True)
    last_job_save_at = models.DateTimeField(null=True, blank=True)
    inactivity_days = models.IntegerField(default=0)
    reactivation_email_sent_at = models.DateTimeField(null=True, blank=True)
    reactivation_count = models.IntegerField(default=0)
    is_inactive = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_inactivity_records"

    def __str__(self):
        return f"Inactivity: {self.user} ({self.inactivity_days} days)"


class DigestQueue(models.Model):
    """Pending recommended jobs for a user's digest email."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="digest_items")
    job_ids = models.JSONField(default=list, help_text="Ordered list of job UUIDs for digest")
    digest_type = models.CharField(max_length=20,
                                   choices=[("daily", "Daily"), ("weekly", "Weekly")], default="weekly")
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_job_id = models.UUIDField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_digest_queues"
        ordering = ["scheduled_for"]

    def __str__(self):
        return f"Digest ({self.digest_type}): {self.user} @ {self.scheduled_for.date()}"
