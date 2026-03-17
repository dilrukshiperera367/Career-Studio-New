"""
Documents & Policies models.
Covers: DocumentTemplate, GeneratedDocument, PolicyDocument, PolicyAcknowledgement.
"""

import uuid
from django.db import models
from django.conf import settings


class DocumentTemplate(models.Model):
    """Reusable HR document template (offer letter, warning letter, etc.)."""

    TEMPLATE_TYPE_CHOICES = [
        ('offer_letter', 'Offer Letter'),
        ('warning_letter', 'Warning Letter'),
        ('employment_certificate', 'Employment Certificate'),
        ('nda', 'NDA'),
        ('policy_acknowledgement', 'Policy Acknowledgement'),
        ('contract', 'Contract'),
        ('custom', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='document_templates'
    )
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPE_CHOICES)
    description = models.TextField(blank=True)
    content = models.TextField(
        help_text='HTML/Markdown template with {{variable}} placeholders'
    )
    variables = models.JSONField(
        default=list,
        help_text='[{"key": "employee_name", "label": "Employee Name", "required": true}]'
    )
    version = models.CharField(max_length=20, default='1.0')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_document_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'documents_policies'
        db_table = 'document_templates'

    def __str__(self):
        return f"{self.name} (v{self.version})"


class GeneratedDocument(models.Model):
    """A document generated from a template for a specific employee."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_signature', 'Pending Signature'),
        ('signed', 'Signed'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    E_SIGN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='generated_documents'
    )
    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='generated_documents'
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='generated_documents'
    )
    title = models.CharField(max_length=300)
    content = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='generated_documents'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    variables_used = models.JSONField(default=dict)
    file_url = models.CharField(max_length=500, blank=True)
    e_sign_provider = models.CharField(max_length=50, blank=True)
    e_sign_request_id = models.CharField(max_length=200, blank=True)
    e_sign_status = models.CharField(
        max_length=20, choices=E_SIGN_STATUS_CHOICES, default='pending'
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'documents_policies'
        db_table = 'generated_documents'
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.title} ({self.employee})"


class PolicyDocument(models.Model):
    """Company policy document (employee handbook, code of conduct, etc.)."""

    CATEGORY_CHOICES = [
        ('hr_policy', 'HR Policy'),
        ('code_of_conduct', 'Code of Conduct'),
        ('safety', 'Safety'),
        ('data_privacy', 'Data Privacy'),
        ('leave', 'Leave'),
        ('benefits', 'Benefits'),
        ('it_security', 'IT Security'),
        ('custom', 'Custom'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='policy_documents'
    )
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    version = models.CharField(max_length=20)
    content = models.TextField()
    summary = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    requires_acknowledgement = models.BooleanField(default=True)
    effective_date = models.DateField()
    review_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    target_audience = models.JSONField(
        default=dict,
        help_text='{"departments": [], "grades": [], "all": true}'
    )
    attachments = models.JSONField(default=list)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_policy_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'documents_policies'
        db_table = 'policy_documents'
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} (v{self.version})"


class PolicyAcknowledgement(models.Model):
    """Employee acknowledgement of a policy document."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='policy_acknowledgements'
    )
    policy = models.ForeignKey(
        PolicyDocument, on_delete=models.CASCADE, related_name='acknowledgements'
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='policy_acknowledgements'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    is_acknowledged = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        app_label = 'documents_policies'
        db_table = 'policy_acknowledgements'
        unique_together = ['policy', 'employee']

    def __str__(self):
        return f"{self.employee} — {self.policy.title}"
