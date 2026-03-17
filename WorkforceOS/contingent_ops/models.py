"""
Contingent Workforce Operations models.
Covers: Vendor, ContingentWorker, ContingentTimesheet, ContingentCompliance.
"""

import uuid
from django.db import models
from django.conf import settings


class Vendor(models.Model):
    """Staffing agency / vendor."""

    COMPLIANCE_STATUS_CHOICES = [
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('under_review', 'Under Review'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='vendors'
    )
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200, blank=True)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=2, blank=True)
    preferred = models.BooleanField(default=False)
    compliance_status = models.CharField(
        max_length=20, choices=COMPLIANCE_STATUS_CHOICES, default='under_review'
    )
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'contingent_ops'
        db_table = 'vendors'
        ordering = ['name']

    def __str__(self):
        return self.name


class ContingentWorker(models.Model):
    """Contractor/temp worker record."""

    WORKER_TYPE_CHOICES = [
        ('contractor', 'Contractor'),
        ('temp', 'Temp'),
        ('consultant', 'Consultant'),
        ('freelancer', 'Freelancer'),
        ('intern', 'Intern'),
    ]

    RATE_TYPE_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
        ('fixed', 'Fixed'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]

    BG_CHECK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('not_required', 'Not Required'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='contingent_workers'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    worker_type = models.CharField(
        max_length=20, choices=WORKER_TYPE_CHOICES, default='contractor'
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='workers'
    )
    department = models.ForeignKey(
        'core_hr.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contingent_workers'
    )
    manager = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='contingent_team'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    contract_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rate_currency = models.CharField(max_length=3, default='LKR')
    rate_type = models.CharField(
        max_length=20, choices=RATE_TYPE_CHOICES, default='hourly'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    nda_signed = models.BooleanField(default=False)
    bg_check_status = models.CharField(
        max_length=20, choices=BG_CHECK_STATUS_CHOICES, default='not_required'
    )
    access_granted = models.JSONField(
        default=list, help_text='Systems/tools this worker has been granted access to'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'contingent_ops'
        db_table = 'contingent_workers'
        ordering = ['-start_date']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class ContingentTimesheet(models.Model):
    """Timesheet submission for a contingent worker."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='contingent_timesheets'
    )
    worker = models.ForeignKey(
        ContingentWorker, on_delete=models.CASCADE, related_name='timesheets'
    )
    week_start = models.DateField()
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    daily_hours = models.JSONField(
        default=dict,
        help_text='{"Mon": 8.0, "Tue": 8.0, "Wed": 8.0, "Thu": 8.0, "Fri": 8.0}'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_contingent_timesheets'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'contingent_ops'
        db_table = 'contingent_timesheets'
        unique_together = ['worker', 'week_start']
        ordering = ['-week_start']

    def __str__(self):
        return f"{self.worker} — w/c {self.week_start} ({self.status})"


class ContingentCompliance(models.Model):
    """Compliance/document tracking for a contingent worker."""

    REQUIREMENT_TYPE_CHOICES = [
        ('nda', 'NDA'),
        ('background_check', 'Background Check'),
        ('insurance', 'Insurance'),
        ('certification', 'Certification'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='contingent_compliance_records'
    )
    worker = models.ForeignKey(
        ContingentWorker, on_delete=models.CASCADE, related_name='compliance_records'
    )
    requirement_type = models.CharField(max_length=30, choices=REQUIREMENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expiry_date = models.DateField(null=True, blank=True)
    document_url = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    last_reviewed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'contingent_ops'
        db_table = 'contingent_compliance'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.worker} — {self.title} ({self.status})"
