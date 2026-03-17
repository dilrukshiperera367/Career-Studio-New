import uuid
from django.db import models
from django.conf import settings


class Credential(models.Model):
    """A verifiable credential owned by a person."""
    TYPE_CERTIFICATE = 'certificate'
    TYPE_LICENSE = 'license'
    TYPE_BADGE = 'badge'
    TYPE_ASSESSMENT = 'assessment'
    TYPE_PORTFOLIO = 'portfolio'
    TYPE_ENDORSEMENT = 'endorsement'
    TYPE_DEGREE = 'degree'
    TYPE_CHOICES = [
        (TYPE_CERTIFICATE, 'Certificate'),
        (TYPE_LICENSE, 'License'),
        (TYPE_BADGE, 'Digital Badge'),
        (TYPE_ASSESSMENT, 'Assessment Result'),
        (TYPE_PORTFOLIO, 'Portfolio Item'),
        (TYPE_ENDORSEMENT, 'Endorsement'),
        (TYPE_DEGREE, 'Degree'),
    ]

    STATUS_VERIFIED = 'verified'
    STATUS_PENDING = 'pending'
    STATUS_EXPIRED = 'expired'
    STATUS_UNVERIFIED = 'unverified'
    STATUS_REVOKED = 'revoked'
    STATUS_CHOICES = [
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_PENDING, 'Pending Verification'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_UNVERIFIED, 'Unverified'),
        (STATUS_REVOKED, 'Revoked'),
    ]

    SOURCE_MANUAL = 'manual'
    SOURCE_IMPORT = 'import'
    SOURCE_OPEN_BADGE = 'open_badge'
    SOURCE_LINKED_IN = 'linkedin'
    SOURCE_PLATFORM = 'platform'
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, 'Manual Entry'),
        (SOURCE_IMPORT, 'Imported'),
        (SOURCE_OPEN_BADGE, 'Open Badge (1EdTech)'),
        (SOURCE_LINKED_IN, 'LinkedIn Import'),
        (SOURCE_PLATFORM, 'Platform Issued'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='credentials'
    )
    title = models.CharField(max_length=500)
    credential_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNVERIFIED)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)

    # Issuer
    issuer_name = models.CharField(max_length=300)
    issuer_url = models.URLField(blank=True)
    issuer_logo_url = models.URLField(blank=True)

    # Dates
    issued_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    # Verification
    credential_url = models.URLField(blank=True, help_text='URL to verify the credential')
    credential_id = models.CharField(
        max_length=300, blank=True,
        help_text='External credential ID for verification'
    )
    badge_json = models.JSONField(
        default=dict, blank=True,
        help_text='Open Badge 2.0/3.0 assertion JSON'
    )

    # Evidence
    evidence_url = models.URLField(blank=True)
    evidence_file = models.FileField(upload_to='credentials/', blank=True)
    description = models.TextField(blank=True)

    # Skills linkage — stored as JSON list of skill IDs until skills_graph app is installed
    linked_skills = models.JSONField(
        default=list, blank=True,
        help_text='Skill IDs validated by this credential (JSON list)'
    )

    # Metadata
    is_public = models.BooleanField(
        default=True, help_text='Show on public profile'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_credentials'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cx_credential'
        ordering = ['-issued_date']

    def __str__(self):
        return f'{self.title} ({self.issuer_name})'

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()

    @property
    def is_expiring_soon(self):
        if not self.expiry_date:
            return False
        import datetime
        from django.utils import timezone
        return (
            not self.is_expired and
            (self.expiry_date - timezone.now().date()).days < 90
        )


class CredentialShare(models.Model):
    """Track when credentials are shared with employers/recruiters."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credential = models.ForeignKey(
        Credential, on_delete=models.CASCADE, related_name='shares'
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_credential_shares'
    )
    shared_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cx_credential_share'
        ordering = ['-shared_at']

    def __str__(self):
        return f'{self.credential.title} → {self.shared_with}'
