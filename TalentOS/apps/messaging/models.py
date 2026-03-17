"""Messaging app — Email templates, messages, activity logging, and notifications."""

import uuid
from django.db import models
from apps.shared.html_sanitizer import sanitize_html


class EmailTemplate(models.Model):
    """Reusable email template per tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="email_templates")
    slug = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=500)
    body = models.TextField(help_text="Template body with {{variable}} placeholders")
    category = models.CharField(
        max_length=50,
        choices=[
            ("application", "Application"),
            ("interview", "Interview"),
            ("rejection", "Rejection"),
            ("offer", "Offer"),
            ("reminder", "Reminder"),
            ("follow_up", "Follow-up"),
            ("acknowledgment", "Acknowledgment"),
            ("onboarding", "Onboarding"),
            ("general", "General"),
        ],
        default="general",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_templates"
        unique_together = [("tenant", "slug")]

    def __str__(self):
        return f"{self.name} ({self.slug})"


class Message(models.Model):
    """A message sent to or from a candidate — with threading and tracking."""

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("scheduled", "Scheduled"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("delivered", "Delivered"),
        ("bounced", "Bounced"),
        ("opened", "Opened"),
    ]

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("in_app", "In-App"),
        ("sms", "SMS"),
    ]

    DIRECTION_CHOICES = [
        ("outbound", "Outbound"),
        ("inbound", "Inbound"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="messages")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="messages"
    )
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="messages"
    )
    sender = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_messages"
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="email")
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default="outbound")
    subject = models.CharField(max_length=500, blank=True, default="")
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    provider_id = models.CharField(max_length=255, blank=True, default="")
    error = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)

    # Threading (Feature 69)
    thread_id = models.UUIDField(null=True, blank=True, db_index=True,
        help_text="Groups emails into conversation threads")

    # Scheduling (Feature 73)
    scheduled_for = models.DateTimeField(null=True, blank=True,
        help_text="Send at this time instead of immediately")

    # Tracking (Feature 72)
    tracking_id = models.CharField(max_length=100, blank=True, default="")
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    # Template reference
    template_used = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_messages"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
        indexes = [
            models.Index(fields=["tenant", "candidate", "created_at"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "thread_id"]),
            models.Index(fields=["tenant", "scheduled_for"]),
        ]

    def __str__(self):
        return f"{self.channel}: {self.subject[:50]}"


class ActivityLog(models.Model):
    """Audit log of all significant actions (PII access, mutations, logins)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="activity_logs")
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="activity_logs"
    )
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    action = models.CharField(max_length=100)
    content = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        indexes = [
            models.Index(fields=["tenant", "entity_type", "entity_id"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "actor", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}:{self.entity_id}"


# ---------------------------------------------------------------------------
# Offer Letter Templates (#45)
# ---------------------------------------------------------------------------

class OfferLetterTemplate(models.Model):
    """
    Customisable offer letter template per tenant (#45).
    Supports Django-syntax {{variable}} placeholders rendered at PDF generation time.
    Available variables: candidate_name, job_title, department, start_date,
    salary, benefits, equity, signing_bonus, company_name, offer_date, expiry_date.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="offer_letter_templates")
    name = models.CharField(max_length=200, help_text="Internal template name (e.g. 'Standard Offer – Engineering')")
    slug = models.CharField(max_length=100, help_text="Machine-readable identifier, unique per tenant")
    subject_line = models.CharField(max_length=500, default="Offer of Employment — {{company_name}}")
    html_body = models.TextField(
        help_text="Full HTML body with {{variable}} placeholders. Leave blank to use system default."
    )
    is_default = models.BooleanField(
        default=False,
        help_text="If True, this template is used when no template is explicitly selected on an offer."
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_offer_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "offer_letter_templates"
        unique_together = [("tenant", "slug")]
        indexes = [
            models.Index(fields=["tenant", "is_default"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    def save(self, *args, **kwargs):
        # Sanitize HTML to prevent XSS before persisting
        if self.html_body:
            self.html_body = sanitize_html(self.html_body)
        super().save(*args, **kwargs)


class NurtureSequence(models.Model):
    """
    A multi-step nurture sequence for engaging talent pool candidates
    over time — drip campaigns for passive candidates.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="nurture_sequences")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    exit_on_reply = models.BooleanField(default=True, help_text="Stop sequence if candidate replies")
    exit_on_apply = models.BooleanField(default=True, help_text="Stop sequence if candidate applies")
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_sequences",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nurture_sequences"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Nurture: {self.name}"


class NurtureStep(models.Model):
    """A single step (message) in a NurtureSequence."""

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("in_app", "In-App"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(NurtureSequence, on_delete=models.CASCADE, related_name="steps")
    step_order = models.IntegerField(default=1)
    delay_days = models.IntegerField(default=0, help_text="Days after previous step (or enrollment for step 1)")
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="email")
    subject = models.CharField(max_length=500, blank=True, default="")
    body = models.TextField()
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="nurture_steps",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nurture_steps"
        ordering = ["sequence", "step_order"]
        unique_together = [("sequence", "step_order")]

    def __str__(self):
        return f"Step {self.step_order} of {self.sequence.name}"


class NurtureEnrollment(models.Model):
    """A candidate enrolled in a NurtureSequence."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("exited", "Exited"),
        ("paused", "Paused"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="nurture_enrollments")
    sequence = models.ForeignKey(NurtureSequence, on_delete=models.CASCADE, related_name="enrollments")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="nurture_enrollments"
    )
    current_step = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    exit_reason = models.CharField(max_length=50, blank=True, default="")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    next_send_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "nurture_enrollments"
        unique_together = [("sequence", "candidate")]
        ordering = ["-enrolled_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "next_send_at"]),
        ]

    def __str__(self):
        return f"Enrollment: {self.candidate_id} in {self.sequence.name}"


class CommunicationPreferenceCenter(models.Model):
    """
    Stores a candidate's communication opt-in/opt-out preferences per channel and topic.
    Required for GDPR and CAN-SPAM compliance.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="comm_preferences")
    candidate = models.OneToOneField(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="comm_preferences"
    )
    email_job_alerts = models.BooleanField(default=True)
    email_application_updates = models.BooleanField(default=True)
    email_nurture = models.BooleanField(default=False)
    sms_interview_reminders = models.BooleanField(default=False)
    sms_offers = models.BooleanField(default=False)
    global_opt_out = models.BooleanField(default=False, help_text="Opted out of all communications")
    opt_out_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "communication_preferences"

    def __str__(self):
        return f"CommPrefs for {self.candidate_id}"


class BulkCampaign(models.Model):
    """
    A bulk outreach campaign targeting a segment of candidates.
    Supports email and SMS blasts with scheduling.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="bulk_campaigns")
    name = models.CharField(max_length=255)
    channel = models.CharField(
        max_length=10,
        choices=[("email", "Email"), ("sms", "SMS")],
        default="email",
    )
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bulk_campaigns",
    )
    subject = models.CharField(max_length=500, blank=True, default="")
    body = models.TextField(blank=True, default="")
    segment_query = models.JSONField(
        default=dict, blank=True,
        help_text='{"pool_status": "active", "talent_tier": "gold", "skills": [...]}'
    )
    recipient_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bulk_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bulk_campaigns"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self):
        return f"Campaign: {self.name} ({self.status})"

