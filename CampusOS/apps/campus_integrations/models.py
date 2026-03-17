"""CampusOS — Campus Integrations models (SIS, LMS, SSO, cross-platform)."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class SISIntegration(TimestampedModel):
    """Student Information System (SIS) connection config."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.OneToOneField("campus.Campus", on_delete=models.CASCADE, related_name="sis_integration")

    SIS_TYPE_CHOICES = [
        ("sap", "SAP ERP"),
        ("oracle", "Oracle Student Cloud"),
        ("ellucian", "Ellucian Banner"),
        ("custom_api", "Custom REST API"),
        ("csv_upload", "CSV Upload"),
        ("sftp", "SFTP Sync"),
    ]

    sis_type = models.CharField(max_length=20, choices=SIS_TYPE_CHOICES)
    endpoint_url = models.URLField(blank=True)
    auth_method = models.CharField(
        max_length=20,
        choices=[("api_key", "API Key"), ("oauth2", "OAuth 2.0"), ("basic", "Basic Auth"), ("none", "No Auth")],
        default="api_key",
    )
    # Stored encrypted in production — here as placeholder
    api_key_hint = models.CharField(max_length=10, blank=True, help_text="Last 4 chars of API key")
    sync_frequency = models.CharField(
        max_length=15,
        choices=[("realtime", "Real-time"), ("daily", "Daily"), ("weekly", "Weekly"), ("manual", "Manual")],
        default="daily",
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(
        max_length=15,
        choices=[("success", "Success"), ("failed", "Failed"), ("partial", "Partial"), ("never", "Never")],
        default="never",
    )
    is_active = models.BooleanField(default=False)
    sync_log = models.JSONField(default=list)


class LMSIntegration(TimestampedModel):
    """Learning Management System connection config."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.OneToOneField("campus.Campus", on_delete=models.CASCADE, related_name="lms_integration")

    LMS_TYPE_CHOICES = [
        ("moodle", "Moodle"),
        ("canvas", "Canvas"),
        ("blackboard", "Blackboard"),
        ("google_classroom", "Google Classroom"),
        ("microsoft_teams", "Microsoft Teams EDU"),
        ("custom", "Custom"),
    ]

    lms_type = models.CharField(max_length=25, choices=LMS_TYPE_CHOICES)
    base_url = models.URLField(blank=True)
    api_key_hint = models.CharField(max_length=10, blank=True)
    sync_grades = models.BooleanField(default=True)
    sync_attendance = models.BooleanField(default=False)
    sync_courses = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)


class SSOConfiguration(TimestampedModel):
    """SSO config for university identity provider."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.OneToOneField("campus.Campus", on_delete=models.CASCADE, related_name="sso_config")

    SSO_PROTOCOL_CHOICES = [
        ("saml2", "SAML 2.0"),
        ("oidc", "OpenID Connect"),
        ("oauth2", "OAuth 2.0"),
        ("ldap", "LDAP / Active Directory"),
        ("google_workspace", "Google Workspace"),
        ("microsoft_entra", "Microsoft Entra ID"),
    ]

    protocol = models.CharField(max_length=20, choices=SSO_PROTOCOL_CHOICES)
    idp_entity_id = models.CharField(max_length=500, blank=True)
    idp_sso_url = models.URLField(blank=True)
    idp_cert_hint = models.CharField(max_length=20, blank=True)
    email_domain = models.CharField(max_length=200, blank=True, help_text="e.g. students.university.lk")
    is_active = models.BooleanField(default=False)
    is_mandatory = models.BooleanField(default=False, help_text="Force SSO for all users")


class CrossPlatformSync(TimestampedModel):
    """Tracks sync operations with peer platforms (CareerOS, TalentOS, etc)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="platform_syncs")

    PLATFORM_CHOICES = [
        ("careeros", "CareerOS"),
        ("talentos", "TalentOS"),
        ("jobfinder", "Job Finder"),
        ("workforceos", "WorkforceOS"),
    ]
    ENTITY_CHOICES = [
        ("student_profile", "Student Profile"),
        ("readiness_score", "Readiness Score"),
        ("placement_outcome", "Placement Outcome"),
        ("employer", "Employer"),
        ("job_listing", "Job Listing"),
        ("credential", "Credential / Badge"),
    ]

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    entity_type = models.CharField(max_length=25, choices=ENTITY_CHOICES)
    local_object_id = models.UUIDField()
    remote_object_id = models.CharField(max_length=200, blank=True)
    direction = models.CharField(
        max_length=10,
        choices=[("push", "Push to Remote"), ("pull", "Pull from Remote"), ("bidirectional", "Bidirectional")],
        default="push",
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed"), ("conflict", "Conflict")],
        default="pending",
    )
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = [["campus", "platform", "entity_type", "local_object_id"]]
        ordering = ["-last_synced_at"]


class WebhookEndpoint(TimestampedModel):
    """Outbound webhook subscription for external systems."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="webhooks")
    url = models.URLField()
    event_types = models.JSONField(default=list, help_text="e.g. ['student.placed', 'internship.completed']")
    secret_hint = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    failure_count = models.PositiveSmallIntegerField(default=0)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_status_code = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.campus} → {self.url}"
