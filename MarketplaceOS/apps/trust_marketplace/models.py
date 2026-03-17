"""
MarketplaceOS — apps.trust_marketplace

Trust, Safety & Quality Control.

Models:
    ProviderReport      — Buyer-submitted complaint / abuse report about a provider
    ProviderStrike      — Platform-issued strike record on a provider
    Dispute             — Payment / booking dispute between buyer and provider
    DisputeResolution   — Admin resolution record for a dispute
    SafeMessagingRule   — Platform rules for the messaging system (scam patterns, etc.)
    QualityScore        — Composite quality score per provider (computed by platform)
    RiskFlag            — Platform-generated risk signal on a user or transaction
    BackgroundCheckRecord — Provider background check status
"""
import uuid
from django.db import models
from django.conf import settings


class ProviderReport(models.Model):
    """
    Buyer-submitted complaint or abuse report about a provider.
    Feeds the moderation queue.
    """

    class ReportType(models.TextChoices):
        FRAUD = "fraud", "Fraud / Scam"
        NO_SHOW = "no_show", "No-Show"
        POOR_QUALITY = "poor_quality", "Poor Service Quality"
        HARASSMENT = "harassment", "Harassment / Abuse"
        IMPERSONATION = "impersonation", "Impersonation"
        CREDENTIAL_FRAUD = "credential_fraud", "Fake Credentials"
        GUIDELINE_VIOLATION = "guideline_violation", "Platform Guideline Violation"
        OTHER = "other", "Other"

    class ReportStatus(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"
        ESCALATED = "escalated", "Escalated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_reports",
    )
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="reports",
    )
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.SET_NULL, null=True, blank=True,
    )
    report_type = models.CharField(max_length=25, choices=ReportType.choices)
    description = models.TextField()
    evidence_urls = models.JSONField(default=list, help_text="URLs to supporting screenshots/files.")
    status = models.CharField(max_length=15, choices=ReportStatus.choices, default=ReportStatus.OPEN)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_reports",
    )
    resolution_notes = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_provider_report"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report ({self.report_type}) on {self.provider} — {self.status}"


class ProviderStrike(models.Model):
    """Platform-issued strike against a provider for policy violations."""

    class StrikeType(models.TextChoices):
        NO_SHOW = "no_show", "No-Show"
        FRAUD = "fraud", "Fraud"
        GUIDELINE_VIOLATION = "guideline_violation", "Guideline Violation"
        HARASSMENT = "harassment", "Harassment"
        CREDENTIAL_FRAUD = "credential_fraud", "Credential Fraud"
        REVIEW_MANIPULATION = "review_manipulation", "Review Manipulation"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="strikes",
    )
    report = models.ForeignKey(ProviderReport, on_delete=models.SET_NULL, null=True, blank=True)
    strike_type = models.CharField(max_length=25, choices=StrikeType.choices)
    severity = models.IntegerField(default=1, help_text="1 = warning, 2 = strike, 3 = final warning")
    description = models.TextField()
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mp_provider_strike"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Strike {self.severity} on {self.provider} ({self.strike_type})"


class Dispute(models.Model):
    """
    Payment or booking dispute between a buyer and provider.
    Admin-mediated resolution.
    """

    class DisputeType(models.TextChoices):
        SERVICE_NOT_DELIVERED = "not_delivered", "Service Not Delivered"
        QUALITY_ISSUE = "quality", "Quality Not as Described"
        NO_SHOW = "no_show", "Provider No-Show"
        REFUND_REJECTED = "refund_rejected", "Refund Rejected Unfairly"
        UNAUTHORIZED_CHARGE = "unauthorized", "Unauthorized Charge"
        OTHER = "other", "Other"

    class DisputeStatus(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        AWAITING_PROVIDER = "awaiting_provider", "Awaiting Provider Response"
        AWAITING_BUYER = "awaiting_buyer", "Awaiting Buyer Evidence"
        RESOLVED_BUYER = "resolved_buyer", "Resolved — Buyer Favor"
        RESOLVED_PROVIDER = "resolved_provider", "Resolved — Provider Favor"
        RESOLVED_SPLIT = "resolved_split", "Resolved — Split"
        ESCALATED = "escalated", "Escalated to Legal"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=20, unique=True, db_index=True)
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.PROTECT, related_name="dispute",
    )
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dispute_type = models.CharField(max_length=25, choices=DisputeType.choices)
    description = models.TextField()
    evidence_urls = models.JSONField(default=list)
    status = models.CharField(max_length=25, choices=DisputeStatus.choices, default=DisputeStatus.OPEN)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_disputes",
    )
    resolution_amount_to_buyer_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    resolution_notes = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_dispute"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispute {self.reference} — {self.status}"

    def save(self, *args, **kwargs):
        if not self.reference:
            import random, string
            self.reference = "DSP-" + "".join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)


class DisputeResolution(models.Model):
    """Admin resolution note / decision for a dispute."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name="resolutions")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    decision = models.TextField()
    refund_amount_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    internal_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_dispute_resolution"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Resolution for {self.dispute}"


class SafeMessagingRule(models.Model):
    """
    Platform-level safe messaging rules: detect scam patterns,
    off-platform contact attempts, personal info leaks.
    """

    class RuleAction(models.TextChoices):
        BLOCK = "block", "Block Message"
        FLAG = "flag", "Flag for Review"
        WARN = "warn", "Warn Sender"
        LOG = "log", "Log Only"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    pattern = models.CharField(max_length=500, help_text="Regex pattern or keyword list (JSON array).")
    pattern_type = models.CharField(max_length=10, choices=[("regex", "Regex"), ("keywords", "Keywords")], default="keywords")
    action = models.CharField(max_length=10, choices=RuleAction.choices, default=RuleAction.FLAG)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_safe_messaging_rule"

    def __str__(self):
        return f"{self.name} — {self.action}"


class QualityScore(models.Model):
    """
    Composite quality score computed by the platform for a provider.
    Factored from: reviews, completion rate, response time, cancel rate, strikes.
    """
    provider = models.OneToOneField(
        "providers.Provider", on_delete=models.CASCADE, related_name="quality_score_record",
    )
    composite_score = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                           help_text="0–100 composite quality score.")
    review_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completion_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    response_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    strike_penalty = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tier = models.CharField(max_length=20, default="standard",
                             help_text="standard | rising | top | elite | at_risk")
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_quality_score"

    def __str__(self):
        return f"QualityScore {self.composite_score} — {self.provider}"


class RiskFlag(models.Model):
    """Platform-generated risk signal on a user or payment."""

    class RiskType(models.TextChoices):
        FRAUD_PAYMENT = "fraud_payment", "Suspected Payment Fraud"
        CHARGEBACK_RISK = "chargeback_risk", "Chargeback Risk"
        IMPERSONATION = "impersonation", "Impersonation"
        MULTIPLE_ACCOUNTS = "multi_account", "Multiple Accounts"
        REVIEW_FRAUD = "review_fraud", "Review Manipulation"
        ACCOUNT_TAKEOVER = "account_takeover", "Account Takeover Signal"
        SPAM = "spam", "Spam Activity"

    class FlagStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INVESTIGATED = "investigated", "Investigated"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="risk_flags")
    risk_type = models.CharField(max_length=20, choices=RiskType.choices)
    description = models.TextField()
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=FlagStatus.choices, default=FlagStatus.ACTIVE)
    evidence = models.JSONField(default=dict)
    detected_at = models.DateTimeField(auto_now_add=True)
    investigated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_risk_flag"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"RiskFlag {self.risk_type} on {self.user} ({self.status})"


class BackgroundCheckRecord(models.Model):
    """Provider background check status (where jurisdictionally required)."""

    class CheckStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        CLEARED = "cleared", "Cleared"
        FLAGGED = "flagged", "Flagged"
        DECLINED = "declined", "Declined"
        WAIVED = "waived", "Waived (Jurisdiction)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="background_checks",
    )
    check_status = models.CharField(max_length=15, choices=CheckStatus.choices, default=CheckStatus.PENDING)
    vendor = models.CharField(max_length=100, blank=True, default="",
                               help_text="Background check vendor name.")
    vendor_reference = models.CharField(max_length=200, blank=True, default="")
    cleared_at = models.DateTimeField(null=True, blank=True)
    flagged_reason = models.TextField(blank=True, default="")
    admin_notes = models.TextField(blank=True, default="")
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "mp_background_check"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"BG Check {self.check_status} — {self.provider}"
