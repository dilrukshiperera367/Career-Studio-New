"""Consent app — GDPR/privacy consent tracking and data requests."""

import uuid
from django.db import models


class ConsentRecord(models.Model):
    """Track candidate consent for data processing."""

    CONSENT_TYPES = [
        ("data_processing", "Data Processing"),
        ("marketing", "Marketing"),
        ("third_party_sharing", "Third Party Sharing"),
        ("retention", "Data Retention"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="consents"
    )
    consent_type = models.CharField(max_length=30, choices=CONSENT_TYPES)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "consent_records"
        indexes = [
            models.Index(fields=["tenant", "candidate", "consent_type"]),
        ]

    def __str__(self):
        status = "granted" if self.granted else "revoked"
        return f"{self.consent_type}: {status}"


class DataRequest(models.Model):
    """GDPR data export/deletion requests."""

    REQUEST_TYPES = [
        ("export", "Data Export"),
        ("delete", "Data Deletion"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="data_requests"
    )
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    result_url = models.CharField(max_length=500, blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_requests"

    def __str__(self):
        return f"{self.request_type} — {self.status}"
