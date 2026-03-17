"""Tenant models — multi-tenancy foundation."""

import uuid
from django.db import models


class Tenant(models.Model):
    """
    Top-level tenant (organization/company account).
    Every data record in the system is scoped to a tenant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True, help_text="Subdomain identifier")
    plan = models.CharField(max_length=50, default='free', choices=[
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise'),
    ])
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('trial', 'Trial'),
    ])
    settings_json = models.JSONField(default=dict, blank=True, help_text="Branding, defaults, feature flags")
    hrm_settings = models.JSONField(default=dict, blank=True, help_text="HRM-specific config: active modules, defaults")
    max_employees = models.IntegerField(default=10, help_text="Employee limit based on plan")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.slug})"


class TenantFeature(models.Model):
    """Module activation per tenant — feature flag for module gating."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='features')
    module = models.CharField(max_length=50, choices=[
        ('core_hr', 'Core HR'),
        ('onboarding', 'Onboarding & Offboarding'),
        ('leave_attendance', 'Leave & Attendance'),
        ('payroll', 'Payroll'),
        ('performance', 'Performance & Goals'),
        ('compensation', 'Compensation & Benefits'),
        ('engagement', 'Employee Engagement'),
        ('learning', 'Learning & Development'),
        ('helpdesk', 'HR Helpdesk'),
        ('analytics', 'Analytics'),
        ('integrations', 'Integrations'),
    ])
    tier = models.CharField(max_length=20, default='starter', choices=[
        ('starter', 'Starter'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise'),
    ])
    enabled = models.BooleanField(default=False)
    enabled_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'tenant_features'
        unique_together = ['tenant', 'module']

    def __str__(self):
        return f"{self.tenant.slug} — {self.module} ({'✓' if self.enabled else '✗'})"


class FeatureFlag(models.Model):
    """Granular feature flags for gradual rollout."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='feature_flags', help_text="NULL = global flag")
    flag_key = models.CharField(max_length=100)
    enabled = models.BooleanField(default=False)
    rollout_pct = models.IntegerField(default=100, help_text="Percentage for gradual rollout")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'feature_flags'
        unique_together = ['tenant', 'flag_key']

    def __str__(self):
        scope = self.tenant.slug if self.tenant else 'GLOBAL'
        return f"{scope}:{self.flag_key} ({'✓' if self.enabled else '✗'})"
from .enterprise import *
