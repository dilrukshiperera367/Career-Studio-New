"""
Compliance & AI Governance models — AI model registry, decision logs,
privacy consents, data retention policies, and accessibility config.
"""

import uuid
from django.db import models
from django.conf import settings


class AIModel(models.Model):
    """Registry of AI models used in the system."""

    MODEL_TYPE_CHOICES = [
        ('attrition_prediction', 'Attrition Prediction'),
        ('skill_matching', 'Skill Matching'),
        ('sentiment', 'Sentiment Analysis'),
        ('anomaly_detection', 'Anomaly Detection'),
        ('compensation_benchmarking', 'Compensation Benchmarking'),
        ('custom', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='ai_models'
    )
    name = models.CharField(max_length=200)
    model_type = models.CharField(max_length=40, choices=MODEL_TYPE_CHOICES)
    version = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    training_data_description = models.TextField(blank=True)
    last_trained_at = models.DateField(null=True, blank=True)
    accuracy_metrics = models.JSONField(default=dict)
    bias_assessment = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_ai_models'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    explainability_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'compliance_ai'
        db_table = 'ai_models'

    def __str__(self):
        return f"{self.name} v{self.version}"


class AIDecisionLog(models.Model):
    """Log of AI-driven decisions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='ai_decision_logs'
    )
    ai_model = models.ForeignKey(
        AIModel, on_delete=models.CASCADE,
        related_name='decision_logs'
    )
    entity_type = models.CharField(max_length=50, help_text="e.g. 'Employee'")
    entity_id = models.UUIDField()
    decision_type = models.CharField(max_length=100)
    input_features = models.JSONField(default=dict)
    output = models.JSONField(default=dict)
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    was_overridden = models.BooleanField(default=False)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ai_decision_overrides'
    )
    override_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'compliance_ai'
        db_table = 'ai_decision_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ai_model} — {self.decision_type} ({self.entity_id})"


class PrivacyConsent(models.Model):
    """Employee consent records for data processing."""

    CONSENT_TYPE_CHOICES = [
        ('analytics_data', 'Analytics Data'),
        ('ai_profiling', 'AI Profiling'),
        ('third_party_sharing', 'Third-Party Sharing'),
        ('marketing', 'Marketing'),
        ('all', 'All'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='privacy_consents'
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE,
        related_name='privacy_consents'
    )
    consent_type = models.CharField(max_length=30, choices=CONSENT_TYPE_CHOICES)
    is_granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    consent_version = models.CharField(max_length=20)
    notes = models.TextField(blank=True)

    class Meta:
        app_label = 'compliance_ai'
        db_table = 'privacy_consents'
        unique_together = [['employee', 'consent_type']]

    def __str__(self):
        status = 'granted' if self.is_granted else 'withdrawn'
        return f"{self.employee} — {self.consent_type} ({status})"


class DataRetentionPolicy(models.Model):
    """Per-data-type retention policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='data_retention_policies'
    )
    data_type = models.CharField(max_length=100, help_text="e.g. 'payroll_entries'")
    retention_years = models.IntegerField()
    legal_basis = models.CharField(max_length=200, blank=True)
    auto_delete = models.BooleanField(default=False)
    last_purge_at = models.DateTimeField(null=True, blank=True)
    next_purge_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'compliance_ai'
        db_table = 'data_retention_policies'

    def __str__(self):
        return f"{self.data_type} — {self.retention_years}yr"


class AccessibilityConfig(models.Model):
    """WCAG / accessibility settings per tenant."""

    WCAG_LEVEL_CHOICES = [
        ('A', 'Level A'),
        ('AA', 'Level AA'),
        ('AAA', 'Level AAA'),
    ]

    FONT_SIZE_CHOICES = [
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('xlarge', 'Extra Large'),
    ]

    COLOR_BLIND_CHOICES = [
        ('none', 'None'),
        ('protanopia', 'Protanopia'),
        ('deuteranopia', 'Deuteranopia'),
        ('tritanopia', 'Tritanopia'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='accessibility_config'
    )
    wcag_level = models.CharField(max_length=3, choices=WCAG_LEVEL_CHOICES, default='AA')
    high_contrast_enabled = models.BooleanField(default=False)
    font_size_default = models.CharField(
        max_length=10, choices=FONT_SIZE_CHOICES, default='medium'
    )
    keyboard_nav_enabled = models.BooleanField(default=True)
    screen_reader_hints = models.BooleanField(default=True)
    language_default = models.CharField(max_length=10, default='en')
    rtl_support = models.BooleanField(default=False)
    color_blind_mode = models.CharField(
        max_length=20, choices=COLOR_BLIND_CHOICES, default='none'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'compliance_ai'
        db_table = 'accessibility_configs'

    def __str__(self):
        return f"Accessibility config — {self.tenant}"
