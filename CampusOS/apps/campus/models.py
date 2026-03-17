"""
CampusOS — Campus: Core institution and program data.

Models:
    Campus          — main institution record
    Department      — academic departments within a campus
    Program         — degree/certificate programs offered
    CampusBranch    — physical branches / sub-campuses
    AcademicYear    — academic year / semester calendar
"""

import uuid
from django.db import models


class Campus(models.Model):
    """Root institution record — every user and resource belongs to a Campus."""

    class Type(models.TextChoices):
        UNIVERSITY = "university", "University"
        COLLEGE = "college", "College / Degree-granting Institution"
        POLYTECHNIC = "polytechnic", "Polytechnic / Technical Institute"
        VOCATIONAL = "vocational", "Vocational Training Center"
        COMMUNITY_COLLEGE = "community_college", "Community College"
        PROFESSIONAL_SCHOOL = "professional_school", "Professional / Law / Medical School"
        BOOTCAMP = "bootcamp", "Bootcamp / Coding School"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRIAL = "trial", "Trial"
        SUSPENDED = "suspended", "Suspended"
        INACTIVE = "inactive", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    short_name = models.CharField(max_length=50, blank=True, default="")
    slug = models.SlugField(max_length=100, unique=True)
    institution_type = models.CharField(max_length=25, choices=Type.choices, default=Type.UNIVERSITY)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.TRIAL)

    # Identity
    logo = models.ImageField(upload_to="campus/logos/", null=True, blank=True)
    banner = models.ImageField(upload_to="campus/banners/", null=True, blank=True)
    website = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    accreditation_body = models.CharField(max_length=200, blank=True, default="")
    established_year = models.PositiveSmallIntegerField(null=True, blank=True)

    # Contact
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    address_line1 = models.CharField(max_length=300, blank=True, default="")
    address_line2 = models.CharField(max_length=300, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state_province = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, default="Sri Lanka")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Enrollment
    total_students = models.PositiveIntegerField(default=0)
    active_placement_students = models.PositiveIntegerField(default=0)

    # Feature flags (controlled by billing plan)
    feature_readiness_engine = models.BooleanField(default=True)
    feature_internship_management = models.BooleanField(default=False)
    feature_employer_crm = models.BooleanField(default=False)
    feature_placement_drives = models.BooleanField(default=False)
    feature_alumni_network = models.BooleanField(default=False)
    feature_outcomes_analytics = models.BooleanField(default=False)
    feature_accreditation_reports = models.BooleanField(default=False)
    feature_credential_wallet = models.BooleanField(default=False)

    # Settings
    placement_policy = models.JSONField(
        default=dict,
        help_text="Placement policy rules: one_offer_per_student, dream_company_rules, etc.",
    )
    timezone = models.CharField(max_length=50, default="Asia/Colombo")
    default_language = models.CharField(max_length=10, default="en")
    academic_year_start_month = models.PositiveSmallIntegerField(default=8)

    # External IDs for SIS / LMS integrations
    sis_institution_id = models.CharField(max_length=100, blank=True, default="")
    lms_institution_id = models.CharField(max_length=100, blank=True, default="")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campuses"
        verbose_name = "Campus"
        verbose_name_plural = "Campuses"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CampusBranch(models.Model):
    """Physical branch / satellite campus of an institution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField(blank=True, default="")
    is_main_campus = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campus_branches"
        ordering = ["campus", "name"]

    def __str__(self):
        return f"{self.campus.short_name or self.campus.name} — {self.name}"


class Department(models.Model):
    """Academic department within a campus."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True, default="")
    description = models.TextField(blank=True, default="")
    head_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    branch = models.ForeignKey(
        CampusBranch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="departments",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus_departments"
        unique_together = [["campus", "code"]]
        ordering = ["campus", "name"]

    def __str__(self):
        return f"{self.campus.short_name or self.campus.name} / {self.name}"


class Program(models.Model):
    """Degree / certificate program offered by a department."""

    class DegreeType(models.TextChoices):
        CERTIFICATE = "certificate", "Certificate"
        DIPLOMA = "diploma", "Diploma"
        ASSOCIATE = "associate", "Associate Degree"
        BACHELOR = "bachelor", "Bachelor's Degree"
        HONOURS = "honours", "Honours Degree"
        MASTER = "master", "Master's Degree"
        PHD = "phd", "Doctorate / PhD"
        PROFESSIONAL = "professional", "Professional Qualification"
        SHORT_COURSE = "short_course", "Short Course"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="programs")
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="programs",
    )
    name = models.CharField(max_length=300)
    code = models.CharField(max_length=30, blank=True, default="")
    degree_type = models.CharField(max_length=20, choices=DegreeType.choices)
    duration_years = models.DecimalField(max_digits=4, decimal_places=1, default=4.0)
    total_semesters = models.PositiveSmallIntegerField(default=8)
    description = models.TextField(blank=True, default="")
    specializations = models.JSONField(
        default=list,
        help_text="List of specialization/stream names.",
    )
    target_industries = models.JSONField(default=list)
    typical_roles = models.JSONField(default=list)
    accreditation = models.CharField(max_length=200, blank=True, default="")
    min_gpa_for_placement = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.00,
        help_text="Minimum GPA for placement eligibility.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus_programs"
        ordering = ["campus", "name"]

    def __str__(self):
        return f"{self.name} ({self.degree_type}) — {self.campus.short_name or self.campus.name}"


class AcademicYear(models.Model):
    """Academic year / semester calendar for a campus."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="academic_years")
    name = models.CharField(max_length=50, help_text="e.g. 2025/2026")
    year_start = models.DateField()
    year_end = models.DateField()
    is_current = models.BooleanField(default=False)
    is_placement_season = models.BooleanField(default=False)
    placement_season_start = models.DateField(null=True, blank=True)
    placement_season_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campus_academic_years"
        unique_together = [["campus", "name"]]
        ordering = ["-year_start"]

    def __str__(self):
        return f"{self.campus.short_name or self.campus.name} — {self.name}"
