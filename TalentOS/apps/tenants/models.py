"""Tenants app — Multi-tenancy core with enhanced configuration."""

import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    """A company/organization using the ATS."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    domain = models.CharField(max_length=255, blank=True, default="")
    logo_url = models.URLField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("suspended", "Suspended"), ("trial", "Trial"), ("expired", "Expired")],
        default="trial",
    )
    plan = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("starter", "Starter"), ("pro", "Pro"), ("enterprise", "Enterprise")],
        default="free",
    )
    trial_ends_at = models.DateTimeField(null=True, blank=True, help_text="When the 14-day free trial expires")
    max_jobs = models.IntegerField(default=5, help_text="Job posting limit based on plan")
    max_candidates = models.IntegerField(default=100, help_text="Candidate limit based on plan")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    TRIAL_DURATION_DAYS = 14
    GRACE_PERIOD_DAYS = 3

    class Meta:
        db_table = "tenants"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_trial(self):
        return self.status == "trial"

    @property
    def is_active_subscription(self):
        return self.status in ("active", "trial")

    @property
    def trial_days_remaining(self):
        """Days left in trial. Returns None if not on trial."""
        if not self.is_trial or not self.trial_ends_at:
            return None
        delta = self.trial_ends_at - timezone.now()
        return max(0, delta.days)

    @property
    def is_trial_expired(self):
        """True if trial period has ended."""
        if not self.trial_ends_at:
            return False
        return timezone.now() > self.trial_ends_at

    @property
    def is_in_grace_period(self):
        """True if within grace period after trial expires."""
        if not self.trial_ends_at:
            return False
        grace_end = self.trial_ends_at + timedelta(days=self.GRACE_PERIOD_DAYS)
        return self.trial_ends_at < timezone.now() <= grace_end

    def start_trial(self):
        """Activate 14-day free trial."""
        self.status = "trial"
        self.trial_ends_at = timezone.now() + timedelta(days=self.TRIAL_DURATION_DAYS)
        self.save(update_fields=["status", "trial_ends_at", "updated_at"])

    def activate(self, plan="starter"):
        """Convert from trial to paid plan."""
        self.status = "active"
        self.plan = plan
        self.trial_ends_at = None
        self.save(update_fields=["status", "plan", "trial_ends_at", "updated_at"])

    def expire_trial(self):
        """Mark trial as expired."""
        self.status = "expired"
        self.save(update_fields=["status", "updated_at"])


class TenantSettings(models.Model):
    """Per-tenant configuration — includes career page, GDPR, custom fields, notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="settings")
    idle_threshold_days = models.IntegerField(default=7)
    retention_days = models.IntegerField(default=365)
    candidate_dedup_auto_threshold = models.FloatField(default=0.92)
    candidate_dedup_flag_threshold = models.FloatField(default=0.85)
    default_rejection_template = models.CharField(max_length=100, blank=True, default="")
    allow_anonymous_apply = models.BooleanField(default=True)
    require_consent = models.BooleanField(default=True)
    custom_ranking_weights = models.JSONField(default=dict, blank=True)
    smtp_config = models.JSONField(default=dict, blank=True)

    # Career page configuration (Features 181-190)
    career_page_config = models.JSONField(default=dict, blank=True,
        help_text='{"logo": "url", "colors": {"primary": "#..."}, "banner": "url", '
        '"about_text": "...", "benefits": [...], "testimonials": [...]}')

    # Custom fields (Feature 97)
    custom_fields_config = models.JSONField(default=dict, blank=True,
        help_text='{"candidate": [{"name": "visa_status", "type": "select", "options": [...]}], '
        '"job": [{"name": "clearance_level", "type": "text"}]}')

    # GDPR / Compliance (Features 133-134)
    data_retention_policy_days = models.IntegerField(default=730, help_text="Auto-purge after N days")
    require_2fa = models.BooleanField(default=False)
    session_timeout_minutes = models.IntegerField(default=30)
    pii_masking_enabled = models.BooleanField(default=False)

    # Notification defaults (Feature 98)
    notification_preferences_default = models.JSONField(default=dict, blank=True,
        help_text='{"new_applicant": true, "interview_scheduled": true, ...}')

    # Rate limiting (Feature 138)
    api_rate_limit_per_minute = models.IntegerField(default=100)

    # Default onboarding template (Feature 14)
    default_onboarding_tasks = models.JSONField(default=list, blank=True,
        help_text='[{"title": "...", "category": "it"}, ...]')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenant_settings"

    def __str__(self):
        return f"Settings for {self.tenant.name}"



# Subscription model has been consolidated into apps.accounts.Subscription
# (accounts.Subscription references tenants.Tenant via OneToOneField)
