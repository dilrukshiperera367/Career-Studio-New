"""
Global Workforce models.
Covers: CountryPack, ExpatAssignment, VisaPermit, MultiCurrencyRate.
"""

import uuid
from django.db import models


class CountryPack(models.Model):
    """Country-specific HR configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='country_packs'
    )
    country_code = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2, e.g. 'LK'")
    country_name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3)
    timezone = models.CharField(max_length=50)
    statutory_rules = models.JSONField(
        default=dict,
        help_text='Country-specific statutory/compliance rules'
    )
    holiday_convention = models.CharField(max_length=50, blank=True)
    work_week = models.JSONField(
        default=list,
        help_text='[1,2,3,4,5] — Mon=1, Tue=2, ..., Sun=7'
    )
    standard_work_hours_per_day = models.DecimalField(
        max_digits=4, decimal_places=2, default=8
    )
    is_enabled = models.BooleanField(default=False)
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'global_workforce'
        db_table = 'country_packs'
        unique_together = ['tenant', 'country_code']

    def __str__(self):
        return f"{self.country_name} ({self.country_code})"


class ExpatAssignment(models.Model):
    """Expatriate employee international assignment."""

    ASSIGNMENT_TYPE_CHOICES = [
        ('short_term', 'Short Term'),
        ('long_term', 'Long Term'),
        ('permanent_transfer', 'Permanent Transfer'),
        ('commuter', 'Commuter'),
    ]

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('active', 'Active'),
        ('extended', 'Extended'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='expat_assignments'
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='expat_assignments'
    )
    home_country = models.CharField(max_length=2)
    host_country = models.CharField(max_length=2)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    assignment_type = models.CharField(
        max_length=30, choices=ASSIGNMENT_TYPE_CHOICES, default='long_term'
    )
    home_base_salary = models.DecimalField(max_digits=14, decimal_places=2)
    host_allowances = models.JSONField(
        default=dict,
        help_text='{"housing": 0, "cola": 0, "school": 0, "car": 0}'
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    supporting_family = models.BooleanField(default=False)
    family_members = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'global_workforce'
        db_table = 'expat_assignments'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee} — {self.home_country} → {self.host_country}"


class VisaPermit(models.Model):
    """Employee visa/work permit record."""

    PERMIT_TYPE_CHOICES = [
        ('work_visa', 'Work Visa'),
        ('residence_permit', 'Residence Permit'),
        ('work_permit', 'Work Permit'),
        ('dependent_visa', 'Dependent Visa'),
        ('business_visa', 'Business Visa'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('applied', 'Applied'),
        ('renewal_pending', 'Renewal Pending'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='visa_permits'
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='visa_permits'
    )
    permit_type = models.CharField(max_length=30, choices=PERMIT_TYPE_CHOICES)
    country = models.CharField(max_length=2)
    permit_number = models.CharField(max_length=100)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    supporting_documents = models.JSONField(default=list)
    reminder_days_before = models.IntegerField(default=60)
    reminder_sent = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'global_workforce'
        db_table = 'visa_permits'
        ordering = ['-expiry_date']

    def __str__(self):
        return f"{self.employee} — {self.permit_type} ({self.country})"


class MultiCurrencyRate(models.Model):
    """Exchange rate snapshot for multi-currency payroll."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='multi_currency_rates'
    )
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=16, decimal_places=6)
    effective_date = models.DateField()
    source = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. 'CBSL', 'manual', 'open_exchange_rates'"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'global_workforce'
        db_table = 'multi_currency_rates'
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.from_currency}/{self.to_currency} = {self.rate} ({self.effective_date})"
