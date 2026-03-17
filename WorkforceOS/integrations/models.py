"""
Integrations models — third-party connectors, OAuth credentials, outbound webhooks.
"""

import uuid
from django.db import models


class Integration(models.Model):
    """An installed integration connector for a tenant."""

    CONNECTOR_CHOICES = [
        ('slack', 'Slack'),
        ('google_calendar', 'Google Calendar'),
        ('microsoft_365', 'Microsoft 365'),
        ('linkedin', 'LinkedIn'),
        ('xero', 'Xero'),
        ('quickbooks', 'QuickBooks'),
        ('ats', 'ATS System (Internal)'),
        ('custom_webhook', 'Custom Webhook'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
        ('pending_auth', 'Pending Authorization'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='integrations')
    connector = models.CharField(max_length=50, choices=CONNECTOR_CHOICES)
    name = models.CharField(max_length=255, help_text='Display name, e.g. "Company Slack Workspace"')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    # Credentials are encrypted at rest via integrations.encryption module (#97, #159)
    _credentials_raw = models.JSONField(
        db_column='credentials',
        default=dict, blank=True,
        help_text='Fernet-encrypted OAuth tokens or API keys (see encryption.py)',
    )
    config = models.JSONField(default=dict, blank=True,
                              help_text='Connector-specific config, e.g. channel_id, calendar_id')
    last_sync_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations'
        unique_together = [('tenant', 'connector')]
        ordering = ['connector']

    def __str__(self):
        return f"{self.tenant_id} — {self.connector} ({self.status})"

    # ── Credential encryption helpers ──────────────────────────────────────

    @property
    def credentials(self) -> dict:
        """Return decrypted credentials."""
        from .encryption import decrypt_credentials, is_encrypted
        raw = self._credentials_raw
        if isinstance(raw, str) and is_encrypted(raw):
            return decrypt_credentials(raw)
        # Plain dict (legacy rows or first-time set) — return as-is
        return raw if isinstance(raw, dict) else {}

    @credentials.setter
    def credentials(self, value: dict) -> None:
        """Encrypt credentials before storing."""
        from .encryption import encrypt_credentials
        if value:
            self._credentials_raw = encrypt_credentials(value)
        else:
            self._credentials_raw = {}


class WebhookRegistration(models.Model):
    """Outbound webhook configuration — HRM pushes events to an external URL."""

    EVENT_CHOICES = [
        # Employee lifecycle
        ('employee.created', 'Employee Created'),
        ('employee.updated', 'Employee Updated'),
        ('employee.terminated', 'Employee Terminated'),
        # Payroll
        ('payroll.finalized', 'Payroll Finalized'),
        ('payslip.generated', 'Payslip Generated'),
        # Leave
        ('leave.approved', 'Leave Approved'),
        ('leave.rejected', 'Leave Rejected'),
        # Performance
        ('review.finalized', 'Review Finalized'),
        # Onboarding
        ('onboarding.completed', 'Onboarding Completed'),
        # Generic
        ('*', 'All Events'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='webhook_registrations')
    name = models.CharField(max_length=255)
    target_url = models.URLField(max_length=500)
    events = models.JSONField(default=list, help_text='List of event types to subscribe to')
    secret = models.CharField(max_length=255, blank=True,
                              help_text='HMAC-SHA256 signing secret for payload verification')
    is_active = models.BooleanField(default=True)
    retry_count = models.IntegerField(default=3, help_text='Number of delivery retries on failure')
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_status_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integration_webhook_registrations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} → {self.target_url}"


class WebhookDeliveryLog(models.Model):
    """Log of each outbound webhook delivery attempt (integrations-specific)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(WebhookRegistration, on_delete=models.CASCADE, related_name='delivery_logs')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    attempt_count = models.IntegerField(default=1)
    delivered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'integration_webhook_delivery_logs'
        ordering = ['-delivered_at']

    def __str__(self):
        return f"{self.event_type} → {self.webhook.target_url} ({'OK' if self.success else 'FAIL'})"
