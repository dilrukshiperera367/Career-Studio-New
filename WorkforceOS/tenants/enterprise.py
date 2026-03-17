"""
Enterprise Readiness — SSO, SCIM, Feature Flags, i18n, Billing.
Covers T237-T247 from Phase 3.
"""

import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
from django.db import models
from django.conf import settings


# ======================== SSO / SAML 2.0 ========================

class SSOConfiguration(models.Model):
    """SAML 2.0 SSO configuration per tenant."""
    PROVIDERS = [('saml', 'SAML 2.0'), ('oidc', 'OpenID Connect'), ('google', 'Google'), ('microsoft', 'Microsoft Entra')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='sso_config')
    provider = models.CharField(max_length=20, choices=PROVIDERS, default='saml')
    is_enabled = models.BooleanField(default=False)
    idp_entity_id = models.URLField(blank=True, help_text="Identity Provider Entity ID")
    idp_sso_url = models.URLField(blank=True, help_text="IdP SSO Login URL")
    idp_slo_url = models.URLField(blank=True, help_text="IdP Single Logout URL")
    idp_certificate = models.TextField(blank=True, help_text="IdP X.509 certificate (PEM)")
    sp_entity_id = models.URLField(blank=True, help_text="Service Provider Entity ID (this app)")
    sp_acs_url = models.URLField(blank=True, help_text="Assertion Consumer Service URL")
    attribute_mapping = models.JSONField(default=dict, help_text="""
        {"email":"urn:oid:0.9.2342.19200300.100.1.3",
         "first_name":"urn:oid:2.5.4.42","last_name":"urn:oid:2.5.4.4"}
    """)
    force_sso = models.BooleanField(default=False, help_text="Require SSO for all users")
    auto_provision = models.BooleanField(default=True, help_text="Auto-create users on first login")
    default_role = models.CharField(max_length=50, default='employee')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'tenants'
        db_table = 'sso_configurations'


# ======================== SCIM 2.0 ========================

class SCIMConfiguration(models.Model):
    """SCIM 2.0 user/group provisioning config."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='scim_config')
    is_enabled = models.BooleanField(default=False)
    bearer_token = models.CharField(max_length=200, blank=True)
    base_url = models.URLField(blank=True)
    sync_groups = models.BooleanField(default=True)
    sync_users = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=20, default='idle')

    class Meta:
        app_label = 'tenants'
        db_table = 'scim_configurations'


class SCIMSyncLog(models.Model):
    """Log entry for SCIM sync operations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='scim_logs')
    operation = models.CharField(max_length=20)  # create_user, update_user, delete_user, sync_groups
    resource_type = models.CharField(max_length=20)  # User, Group
    resource_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20)  # success, failed
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tenants'
        db_table = 'scim_sync_logs'
        ordering = ['-created_at']



# ======================== SUBSCRIPTION / BILLING ========================

class Subscription(models.Model):
    """SaaS subscription for billing."""
    PLANS = [('starter', 'Starter'), ('professional', 'Professional'), ('enterprise', 'Enterprise')]
    STATUS_CHOICES = [('trial', 'Trial'), ('active', 'Active'), ('past_due', 'Past Due'),
                      ('cancelled', 'Cancelled'), ('suspended', 'Suspended')]
    BILLING_CYCLES = [('monthly', 'Monthly'), ('annual', 'Annual')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField('tenants.Tenant', on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLANS, default='starter')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLES, default='monthly')
    price_per_user = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users = models.IntegerField(default=25)
    current_users = models.IntegerField(default=0)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tenants'
        db_table = 'subscriptions'

    def __str__(self):
        return f"{self.tenant} — {self.plan} ({self.status})"

    @property
    def is_active(self):
        return self.status in ('trial', 'active')

    @property
    def days_remaining(self):
        if self.status == 'trial' and self.trial_ends_at:
            delta = self.trial_ends_at - datetime.now()
            return max(0, delta.days)
        return None


class Invoice(models.Model):
    """Billing invoice."""
    STATUS_CHOICES = [('draft', 'Draft'), ('sent', 'Sent'), ('paid', 'Paid'), ('overdue', 'Overdue')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=20, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    paid_at = models.DateTimeField(null=True, blank=True)
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tenants'
        db_table = 'invoices'
        ordering = ['-created_at']


class BillingHistory(models.Model):
    """
    Immutable log of billing events — payment received, refunds, plan changes.
    Acts as audit trail for the subscription lifecycle (#353).
    """
    EVENT_CHOICES = [
        ('trial_started', 'Trial Started'),
        ('trial_expired', 'Trial Expired'),
        ('subscription_created', 'Subscription Created'),
        ('payment_succeeded', 'Payment Succeeded'),
        ('payment_failed', 'Payment Failed'),
        ('plan_upgraded', 'Plan Upgraded'),
        ('plan_downgraded', 'Plan Downgraded'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('refund_issued', 'Refund Issued'),
        ('invoice_generated', 'Invoice Generated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='billing_history'
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='billing_history',
    )
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    plan_before = models.CharField(max_length=20, blank=True)
    plan_after = models.CharField(max_length=20, blank=True)
    stripe_event_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tenants'
        db_table = 'billing_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant.slug} — {self.event_type} ({self.created_at:%Y-%m-%d})"


# ======================== i18n ========================

class TranslationKey(models.Model):
    """Internationalization translation key-value pairs."""
    LANGUAGES = [('en', 'English'), ('si', 'Sinhala'), ('ta', 'Tamil')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=200, help_text="e.g. 'leave.apply_leave', 'common.save'")
    language = models.CharField(max_length=5, choices=LANGUAGES)
    value = models.TextField()
    module = models.CharField(max_length=50, blank=True, help_text="Module grouping")

    class Meta:
        app_label = 'tenants'
        db_table = 'translation_keys'
        unique_together = ['key', 'language']
        ordering = ['key', 'language']
