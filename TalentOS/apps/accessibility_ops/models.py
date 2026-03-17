"""Accessibility Ops app — WCAG 2.2 conformance, accommodation requests, and demographic consent."""

import uuid
from django.db import models


class WCAGCriterion(models.Model):
    """A WCAG 2.2 success criterion tracked for conformance."""

    LEVEL_CHOICES = [
        ("A", "Level A"),
        ("AA", "Level AA"),
        ("AAA", "Level AAA"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criterion_number = models.CharField(max_length=10, unique=True, help_text="e.g. 1.1.1, 2.4.7")
    name = models.CharField(max_length=255)
    level = models.CharField(max_length=3, choices=LEVEL_CHOICES, default="AA")
    guideline = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    testing_procedure = models.TextField(blank=True, default="")
    wcag_version = models.CharField(max_length=10, default="2.2")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wcag_criteria"
        ordering = ["criterion_number"]

    def __str__(self):
        return f"{self.criterion_number} — {self.name} ({self.level})"


class AccessibilityReview(models.Model):
    """A periodic accessibility audit of a TalentOS UI component or page."""

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("in_progress", "In Progress"),
        ("complete", "Complete"),
        ("remediation_required", "Remediation Required"),
    ]

    SCOPE_CHOICES = [
        ("career_site", "Career Site"),
        ("candidate_portal", "Candidate Portal"),
        ("recruiter_ui", "Recruiter UI"),
        ("email_template", "Email Template"),
        ("pdf_document", "PDF Document"),
        ("api", "API Response"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="accessibility_reviews")
    scope = models.CharField(max_length=30, choices=SCOPE_CHOICES, default="other")
    scope_detail = models.CharField(max_length=255, blank=True, default="", help_text="e.g. URL, component name")
    review_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="planned")
    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accessibility_reviews_conducted"
    )
    tool_used = models.CharField(
        max_length=100, blank=True, default="",
        help_text="e.g. axe-core, WAVE, manual screen reader"
    )
    conformance_level_target = models.CharField(max_length=3, default="AA")
    overall_result = models.CharField(
        max_length=20, blank=True, default="",
        help_text="pass / fail / partial"
    )
    issues_found = models.IntegerField(default=0)
    issues_resolved = models.IntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    next_review_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accessibility_reviews"
        ordering = ["-review_date"]

    def __str__(self):
        return f"A11y review: {self.scope_detail or self.scope} ({self.review_date})"


class AccessibilityEvidence(models.Model):
    """An individual WCAG criterion result within an accessibility review."""

    RESULT_CHOICES = [
        ("pass", "Pass"),
        ("fail", "Fail"),
        ("not_applicable", "Not Applicable"),
        ("not_tested", "Not Tested"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="accessibility_evidence")
    review = models.ForeignKey(AccessibilityReview, on_delete=models.CASCADE, related_name="evidence")
    criterion = models.ForeignKey(WCAGCriterion, on_delete=models.PROTECT, related_name="evidence")
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default="not_tested")
    finding = models.TextField(blank=True, default="")
    screenshot_url = models.URLField(blank=True, default="")
    remediation_ticket_url = models.URLField(blank=True, default="")
    remediated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accessibility_evidence"
        ordering = ["review", "criterion__criterion_number"]
        unique_together = [("review", "criterion")]

    def __str__(self):
        return f"{self.criterion.criterion_number} — {self.result} ({self.review_id})"


class AccommodationRequest(models.Model):
    """A candidate's request for a reasonable accommodation during the hiring process."""

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("reviewing", "Reviewing"),
        ("approved", "Approved"),
        ("partially_approved", "Partially Approved"),
        ("denied", "Denied"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="accommodation_requests")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="accommodation_requests"
    )
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accommodation_requests"
    )
    accommodation_type = models.CharField(
        max_length=255,
        help_text="e.g. Extended assessment time, Screen reader, Sign language interpreter"
    )
    description = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")
    approved_accommodation = models.TextField(
        blank=True, default="", help_text="What was actually provided"
    )
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accommodation_reviews"
    )
    denial_reason = models.TextField(blank=True, default="")
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accommodation_requests"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Accommodation: {self.accommodation_type} ({self.status})"


class AccessibilityPreference(models.Model):
    """A candidate's persisted accessibility preferences for their portal experience."""

    CONTRAST_CHOICES = [
        ("default", "Default"),
        ("high_contrast", "High Contrast"),
        ("dark_mode", "Dark Mode"),
    ]

    FONT_SIZE_CHOICES = [
        ("default", "Default"),
        ("large", "Large"),
        ("x_large", "Extra Large"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="accessibility_preferences")
    candidate = models.OneToOneField(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="a11y_ops_preference"
    )
    contrast_mode = models.CharField(max_length=20, choices=CONTRAST_CHOICES, default="default")
    font_size = models.CharField(max_length=20, choices=FONT_SIZE_CHOICES, default="default")
    reduce_motion = models.BooleanField(default=False)
    screen_reader_optimised = models.BooleanField(default=False)
    captions_preferred = models.BooleanField(default=False)
    keyboard_nav_only = models.BooleanField(default=False)
    custom_preferences = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "a11y_ops_preferences"

    def __str__(self):
        return f"A11y prefs — candidate {self.candidate_id}"


class DemographicDataPermission(models.Model):
    """A candidate's granular consent for collection of voluntary demographic data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="demographic_permissions"
    )
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="demographic_permissions"
    )
    allow_gender = models.BooleanField(default=False)
    allow_ethnicity = models.BooleanField(default=False)
    allow_disability = models.BooleanField(default=False)
    allow_age_band = models.BooleanField(default=False)
    allow_veteran_status = models.BooleanField(default=False)
    allow_pronouns = models.BooleanField(default=False)
    consent_version = models.CharField(max_length=20, blank=True, default="")
    consented_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "demographic_data_permissions"
        ordering = ["-consented_at"]

    def __str__(self):
        return f"Demographic consent — candidate {self.candidate_id}"
