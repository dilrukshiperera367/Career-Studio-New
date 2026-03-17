import uuid
from django.db import models
from django.conf import settings


class CommunicationTemplate(models.Model):
    """Reusable message templates for all channels."""
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_PUSH = 'push'
    CHANNEL_IN_APP = 'in_app'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_PUSH, 'Push Notification'),
        (CHANNEL_IN_APP, 'In-App'),
    ]

    CATEGORY_RECRUITER_OUTREACH = 'recruiter_outreach'
    CATEGORY_CANDIDATE_REMINDER = 'candidate_reminder'
    CATEGORY_INTERVIEW = 'interview'
    CATEGORY_OFFER = 'offer'
    CATEGORY_ONBOARDING = 'onboarding'
    CATEGORY_LEARNING = 'learning'
    CATEGORY_MENTOR = 'mentor'
    CATEGORY_SYSTEM = 'system'
    CATEGORY_MARKETING = 'marketing'
    CATEGORY_CHOICES = [
        (CATEGORY_RECRUITER_OUTREACH, 'Recruiter Outreach'),
        (CATEGORY_CANDIDATE_REMINDER, 'Candidate Reminder'),
        (CATEGORY_INTERVIEW, 'Interview'),
        (CATEGORY_OFFER, 'Offer'),
        (CATEGORY_ONBOARDING, 'Onboarding'),
        (CATEGORY_LEARNING, 'Learning'),
        (CATEGORY_MENTOR, 'Mentorship'),
        (CATEGORY_SYSTEM, 'System'),
        (CATEGORY_MARKETING, 'Marketing'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=500, blank=True, help_text='For email')
    body = models.TextField(help_text='Template body with {{variable}} placeholders')
    language = models.CharField(max_length=10, default='en')
    is_active = models.BooleanField(default=True)
    organization = models.ForeignKey(
        'employers.EmployerAccount', on_delete=models.CASCADE,
        null=True, blank=True, related_name='comm_templates',
        help_text='NULL = platform default template'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cx_comm_template'
        ordering = ['category', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_channel_display()})'


class CommunicationMessage(models.Model):
    """Unified outbox — every message sent through any channel."""
    STATUS_QUEUED = 'queued'
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_FAILED = 'failed'
    STATUS_BOUNCED = 'bounced'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_SENT, 'Sent'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_BOUNCED, 'Bounced'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        CommunicationTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='messages'
    )
    channel = models.CharField(max_length=20, choices=CommunicationTemplate.CHANNEL_CHOICES)
    category = models.CharField(max_length=30, choices=CommunicationTemplate.CATEGORY_CHOICES)

    # Sender
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='messages_sent'
    )

    # Recipient
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='messages_received'
    )
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)

    # Content
    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    body_html = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Context
    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cx_comm_message'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['channel', 'status']),
        ]

    def __str__(self):
        return f'{self.get_channel_display()} to {self.recipient} ({self.get_status_display()})'


class CommunicationPreference(models.Model):
    """Per-person channel preferences and opt-outs."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='comm_preferences'
    )
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)

    # Category-level opt-outs
    muted_categories = models.JSONField(
        default=list, blank=True,
        help_text='List of category slugs the user has muted'
    )
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cx_comm_preference'

    def __str__(self):
        return f'Preferences for {self.user}'
