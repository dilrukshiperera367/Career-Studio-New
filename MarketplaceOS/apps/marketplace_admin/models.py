"""
MarketplaceOS — apps.marketplace_admin

Marketplace operations and admin tooling.

Models:
    FeatureFlag             — Runtime feature toggles
    AuditLog                — Tamper-evident audit trail
    ProviderApprovalQueueItem — Queued provider applications for review
    ReviewModerationAction  — Admin actions on submitted reviews
    CommissionOverride      — Per-provider commission overrides
    PlatformAnnouncement    — Broadcast messages to user segments
"""
import uuid
from django.db import models
from django.conf import settings


class FeatureFlag(models.Model):
    """Runtime feature flag for A/B tests and gradual rollouts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")
    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.IntegerField(
        default=100,
        help_text="0–100: percentage of users who see this feature.",
    )
    enabled_for_roles = models.JSONField(
        default=list,
        help_text="Empty list = all roles. Otherwise restrict to these roles.",
    )
    metadata = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_feature_flag"
        ordering = ["key"]

    def __str__(self):
        return f"FeatureFlag:{self.key} ({'on' if self.is_enabled else 'off'})"


class AuditLog(models.Model):
    """Append-only audit log for sensitive admin actions."""

    class ActionType(models.TextChoices):
        PROVIDER_APPROVED = "provider_approved", "Provider Approved"
        PROVIDER_SUSPENDED = "provider_suspended", "Provider Suspended"
        REVIEW_MODERATED = "review_moderated", "Review Moderated"
        DISPUTE_RESOLVED = "dispute_resolved", "Dispute Resolved"
        REFUND_APPROVED = "refund_approved", "Refund Approved"
        COMMISSION_CHANGED = "commission_changed", "Commission Changed"
        PAYOUT_PROCESSED = "payout_processed", "Payout Processed"
        USER_BANNED = "user_banned", "User Banned"
        FEATURE_FLAG_CHANGED = "feature_flag_changed", "Feature Flag Changed"
        ANNOUNCEMENT_SENT = "announcement_sent", "Announcement Sent"
        PROMO_CREATED = "promo_created", "Promo Code Created"
        ADMIN_LOGIN = "admin_login", "Admin Login"
        DATA_EXPORT = "data_export", "Data Export"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_actions",
    )
    action_type = models.CharField(max_length=30, choices=ActionType.choices, db_index=True)
    target_model = models.CharField(max_length=100, blank=True, default="")
    target_id = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "mp_audit_log"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"AuditLog {self.action_type} by {self.actor_id} at {self.timestamp}"


class ProviderApprovalQueueItem(models.Model):
    """Tracks provider onboarding applications awaiting admin review."""

    class QueueStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RESUBMIT = "resubmit", "Returned — Resubmit Required"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="approval_queue_items",
    )
    application = models.ForeignKey(
        "providers.ProviderApplication", on_delete=models.CASCADE,
        null=True, blank=True, related_name="queue_items",
    )
    status = models.CharField(max_length=10, choices=QueueStatus.choices, default=QueueStatus.PENDING)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_queue_items",
    )
    reviewer_notes = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    documents_checklist = models.JSONField(
        default=dict,
        help_text="{'id_verified': true, 'credentials_ok': false, ...}",
    )
    priority = models.IntegerField(default=3, help_text="1=urgent, 2=high, 3=normal, 4=low")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_provider_approval_queue"
        ordering = ["priority", "submitted_at"]

    def __str__(self):
        return f"Approval queue for {self.provider} — {self.status}"


class ReviewModerationAction(models.Model):
    """Admin moderation action on a review."""

    class ModerationDecision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ESCALATED = "escalated", "Escalated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(
        "reviews.Review", on_delete=models.CASCADE, related_name="moderation_actions",
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="moderation_actions",
    )
    decision = models.CharField(max_length=10, choices=ModerationDecision.choices)
    reason = models.TextField(blank=True, default="")
    actioned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_review_moderation_action"
        ordering = ["-actioned_at"]

    def __str__(self):
        return f"Moderation {self.decision} on review {self.review_id}"


class CommissionOverride(models.Model):
    """Per-provider commission override (e.g. negotiated enterprise rate)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.OneToOneField(
        "providers.Provider", on_delete=models.CASCADE, related_name="commission_override",
    )
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2,
                                              help_text="Override platform commission %.")
    reason = models.TextField(blank=True, default="")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="commission_overrides",
    )
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_commission_override"

    def __str__(self):
        return f"CommissionOverride for {self.provider} — {self.commission_percent}%"


class PlatformAnnouncement(models.Model):
    """Broadcast announcement to a user segment."""

    class TargetAudience(models.TextChoices):
        ALL = "all", "All Users"
        PROVIDERS = "providers", "All Providers"
        BUYERS = "buyers", "All Buyers"
        ENTERPRISE = "enterprise", "Enterprise Accounts"
        ADMINS = "admins", "Admins Only"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    body = models.TextField()
    target_audience = models.CharField(max_length=15, choices=TargetAudience.choices, default=TargetAudience.ALL)
    action_url = models.CharField(max_length=500, blank=True, default="")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="announcements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_platform_announcement"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Announcement: {self.title} → {self.target_audience}"
