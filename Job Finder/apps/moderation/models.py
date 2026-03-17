"""Moderation app — Content moderation, reports, flags."""
import uuid
from django.db import models
from django.conf import settings


class Report(models.Model):
    """User-submitted reports on jobs, reviews, messages, profiles."""

    class ContentType(models.TextChoices):
        JOB = "job", "Job Listing"
        REVIEW = "review", "Review"
        MESSAGE = "message", "Message"
        EMPLOYER = "employer", "Employer"
        SEEKER = "seeker", "Seeker"

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        FAKE = "fake", "Fake Listing"
        INAPPROPRIATE = "inappropriate", "Inappropriate Content"
        SCAM = "scam", "Potential Scam"
        HARASSMENT = "harassment", "Harassment"
        DISCRIMINATION = "discrimination", "Discrimination"
        MISLEADING = "misleading", "Misleading Information"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWING = "reviewing", "Under Review"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reports_filed")
    content_type = models.CharField(max_length=10, choices=ContentType.choices)
    content_id = models.UUIDField()
    reason = models.CharField(max_length=15, choices=Reason.choices)
    description = models.TextField(blank=True, default="")
    evidence = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports_reviewed")
    resolution_notes = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="idx_report_status"),
            models.Index(fields=["content_type", "content_id"], name="idx_report_content"),
        ]


class ModerationAction(models.Model):
    """Audit trail for moderation actions taken by moderators/admins."""

    class Action(models.TextChoices):
        APPROVE = "approve", "Approved"
        REJECT = "reject", "Rejected"
        SUSPEND = "suspend", "Suspended"
        BAN = "ban", "Banned"
        WARN = "warn", "Warning Issued"
        REMOVE = "remove", "Content Removed"
        RESTORE = "restore", "Content Restored"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True, related_name="actions")
    action = models.CharField(max_length=10, choices=Action.choices)
    target_type = models.CharField(max_length=10)
    target_id = models.UUIDField()
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_moderation_actions"
        ordering = ["-created_at"]


class BannedEntity(models.Model):
    """Banned users, IPs, or domains."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=10, choices=[("user", "User"), ("ip", "IP"), ("domain", "Domain"), ("email", "Email")])
    entity_value = models.CharField(max_length=200)
    reason = models.TextField(blank=True, default="")
    banned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_banned_entities"
        indexes = [
            models.Index(fields=["entity_type", "entity_value"], name="idx_banned_entity"),
        ]
