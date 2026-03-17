"""CampusOS — Credentials Wallet models (Open Badges 3.0 aligned)."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class DigitalBadge(TimestampedModel):
    """A campus-issued digital badge for a skill, achievement, or milestone."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="digital_badges")

    BADGE_TYPE_CHOICES = [
        ("skill", "Skill Badge"),
        ("achievement", "Achievement Badge"),
        ("participation", "Participation Badge"),
        ("readiness", "Readiness Badge"),
        ("placement", "Placement Badge"),
        ("internship", "Internship Completion"),
        ("certification", "Certification"),
        ("custom", "Custom"),
    ]

    name = models.CharField(max_length=200)
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPE_CHOICES)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    criteria_description = models.TextField(help_text="What a student must do to earn this badge")
    skill_tags = models.JSONField(default=list)
    issuer_name = models.CharField(max_length=200, blank=True)
    issuer_url = models.URLField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    ob3_json = models.JSONField(default=dict, help_text="Open Badges 3.0 assertion payload")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StudentBadgeAward(TimestampedModel):
    """A badge awarded to a student."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    badge = models.ForeignKey(DigitalBadge, on_delete=models.CASCADE, related_name="awards")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="badge_awards")
    awarded_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="badges_awarded"
    )
    awarded_at = models.DateTimeField(auto_now_add=True)
    evidence_url = models.URLField(blank=True)
    evidence_description = models.TextField(blank=True)
    is_revoked = models.BooleanField(default=False)
    revoked_reason = models.TextField(blank=True)
    public_share_url = models.URLField(blank=True)
    assertion_id = models.UUIDField(default=uuid.uuid4, unique=True)

    class Meta:
        unique_together = [["badge", "student"]]
        ordering = ["-awarded_at"]

    def __str__(self):
        return f"{self.student} — {self.badge}"


class VerifiedCertification(TimestampedModel):
    """Campus-verified external certification (AWS, Azure, Google, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="verified_certifications")
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE)

    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    credential_id = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    certificate_url = models.URLField(blank=True)
    verification_url = models.URLField(blank=True)

    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="cert_verifications"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    skill_tags = models.JSONField(default=list)

    class Meta:
        ordering = ["-issue_date"]


class MicroCredential(TimestampedModel):
    """Campus-customised micro-credential course bundle."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="micro_credentials")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    skill_domain = models.CharField(max_length=100, blank=True)
    duration_hours = models.PositiveSmallIntegerField(default=0)
    provider = models.CharField(max_length=200, blank=True, help_text="Coursera, NPTEL, etc.")
    is_active = models.BooleanField(default=True)
    badge = models.ForeignKey(DigitalBadge, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["title"]


class MicroCredentialEnrollment(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credential = models.ForeignKey(MicroCredential, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="micro_credential_enrollments")
    STATUS_CHOICES = [
        ("enrolled", "Enrolled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("dropped", "Dropped"),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="enrolled")
    completion_percentage = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_url = models.URLField(blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [["credential", "student"]]


class SkillEvidenceBundle(TimestampedModel):
    """Portfolio-style bundle linking multiple evidence items to a skill claim."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="skill_bundles")
    skill_name = models.CharField(max_length=200)
    proficiency_level = models.CharField(
        max_length=20,
        choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced"), ("expert", "Expert")],
    )
    evidence_items = models.JSONField(default=list, help_text="List of {type, title, url, description} dicts")
    is_public = models.BooleanField(default=True)
    endorsements_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
