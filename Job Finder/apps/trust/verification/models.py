import uuid
from django.db import models
from django.conf import settings


class EmployerVerification(models.Model):
    """Employer/company verification for trust badges."""
    STATUS_PENDING = 'pending'
    STATUS_VERIFIED = 'verified'
    STATUS_REJECTED = 'rejected'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    METHOD_DOMAIN = 'domain'
    METHOD_DOCUMENT = 'document'
    METHOD_MANUAL = 'manual'
    METHOD_CHOICES = [
        (METHOD_DOMAIN, 'Domain Verification'),
        (METHOD_DOCUMENT, 'Document Upload'),
        (METHOD_MANUAL, 'Manual Review'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(
        'employers.EmployerAccount', on_delete=models.CASCADE,
        related_name='verifications'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    domain = models.CharField(max_length=300, blank=True)
    document_url = models.URLField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cx_employer_verification'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.employer} — {self.get_status_display()}'


class RecruiterVerification(models.Model):
    """Recruiter identity verification."""
    STATUS_CHOICES = EmployerVerification.STATUS_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='recruiter_verifications'
    )
    employer = models.ForeignKey(
        'employers.EmployerAccount', on_delete=models.CASCADE,
        null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    linkedin_url = models.URLField(blank=True)
    id_document_url = models.URLField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    trust_score = models.FloatField(default=0.0, help_text='0.0-1.0')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cx_recruiter_verification'

    def __str__(self):
        return f'{self.user} — {self.get_status_display()}'


class FraudReport(models.Model):
    """Scam/fraud reports from users."""
    REPORT_TYPE_JOB = 'fake_job'
    REPORT_TYPE_EMPLOYER = 'fake_employer'
    REPORT_TYPE_MESSAGE = 'suspicious_message'
    REPORT_TYPE_RECRUITER = 'fake_recruiter'
    REPORT_TYPE_PAYMENT = 'payment_scam'
    REPORT_TYPE_CHOICES = [
        (REPORT_TYPE_JOB, 'Fake/Suspicious Job'),
        (REPORT_TYPE_EMPLOYER, 'Fake Employer'),
        (REPORT_TYPE_MESSAGE, 'Suspicious Message'),
        (REPORT_TYPE_RECRUITER, 'Fake Recruiter'),
        (REPORT_TYPE_PAYMENT, 'Payment Scam'),
    ]

    STATUS_NEW = 'new'
    STATUS_INVESTIGATING = 'investigating'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_DISMISSED = 'dismissed'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_INVESTIGATING, 'Investigating'),
        (STATUS_CONFIRMED, 'Confirmed Fraud'),
        (STATUS_DISMISSED, 'Dismissed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='fraud_reports_filed'
    )
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    description = models.TextField()
    evidence_urls = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    risk_score = models.FloatField(default=0.0)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='fraud_reports_reviewed'
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cx_fraud_report'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_report_type_display()} — {self.get_status_display()}'


class TrustScore(models.Model):
    """Computed trust score for employers and recruiters."""
    ENTITY_EMPLOYER = 'employer'
    ENTITY_RECRUITER = 'recruiter'
    ENTITY_CHOICES = [
        (ENTITY_EMPLOYER, 'Employer'),
        (ENTITY_RECRUITER, 'Recruiter'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=20, choices=ENTITY_CHOICES)
    entity_id = models.UUIDField()
    overall_score = models.FloatField(default=0.5)
    verification_score = models.FloatField(default=0.0)
    activity_score = models.FloatField(default=0.0)
    report_score = models.FloatField(default=1.0, help_text='Lower = more reports')
    last_computed = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cx_trust_score'
        unique_together = ['entity_type', 'entity_id']

    def __str__(self):
        return f'{self.entity_type}:{self.entity_id} — {self.overall_score}'
