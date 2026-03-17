"""
CampusOS — Campus Employers: Employer CRM and Partnership Management.

Models:
    CampusEmployer      — employer account on CampusOS
    RecruiterContact    — individual recruiter contacts
    EmployerEngagement  — relationship / visit history log
    EmployerMOU         — MOU/agreement with campus
    EmployerCampusTier  — partner tier classification
"""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class CampusEmployer(TimestampedModel):
    """Employer/company account registered on CampusOS."""

    class EngagementStatus(models.TextChoices):
        PROSPECT = "prospect", "Prospect"
        ACTIVE = "active", "Active Partner"
        INACTIVE = "inactive", "Inactive"
        DO_NOT_CONTACT = "do_not_contact", "Do Not Contact"

    class PartnerTier(models.TextChoices):
        PREFERRED = "preferred", "Preferred Campus Partner"
        STANDARD = "standard", "Standard Partner"
        NEW = "new", "New / Prospective"
        ALUMNI_NETWORK = "alumni_network", "Alumni Network Partner"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="registered_employers"
    )

    # Identity
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=100)
    logo = models.ImageField(upload_to="employers/logos/", null=True, blank=True)
    banner = models.ImageField(upload_to="employers/banners/", null=True, blank=True)
    website = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    industry = models.CharField(max_length=200, blank=True, default="")
    company_size = models.CharField(max_length=50, blank=True, default="")
    hq_city = models.CharField(max_length=100, blank=True, default="")
    hq_country = models.CharField(max_length=100, blank=True, default="Sri Lanka")
    linkedin_url = models.URLField(blank=True, default="")

    # Cultural & brand info for students
    culture_highlights = models.JSONField(default=list)
    benefits_summary = models.JSONField(default=list)
    hiring_timeline = models.TextField(blank=True, default="")
    assessment_process = models.TextField(blank=True, default="")
    graduate_programs = models.JSONField(default=list)
    internship_programs = models.JSONField(default=list)

    # CRM fields
    engagement_status = models.CharField(
        max_length=20, choices=EngagementStatus.choices, default=EngagementStatus.PROSPECT
    )
    partner_tier = models.CharField(
        max_length=20, choices=PartnerTier.choices, default=PartnerTier.NEW
    )
    relationship_manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="managed_employers",
    )
    account_plan_notes = models.TextField(blank=True, default="")

    # Cross-platform reference
    talentos_employer_id = models.CharField(max_length=100, blank=True, default="")
    jobfinder_employer_id = models.CharField(max_length=100, blank=True, default="")

    # Metrics (computed / updated via signals)
    total_hires = models.PositiveIntegerField(default=0)
    total_internships = models.PositiveIntegerField(default=0)
    repeat_hiring_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_interaction_date = models.DateField(null=True, blank=True)

    # Trust / verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verified_employers",
    )

    is_active = models.BooleanField(default=True)
    follows_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "campus_employers"
        unique_together = [["campus", "slug"]]
        ordering = ["-total_hires", "name"]

    def __str__(self):
        return f"{self.name} ({self.campus.short_name or self.campus.name})"


class RecruiterContact(TimestampedModel):
    """Individual recruiter contacts at an employer."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(
        CampusEmployer, on_delete=models.CASCADE, related_name="recruiter_contacts"
    )
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    is_primary_contact = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    user_account = models.OneToOneField(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="recruiter_contact_profile",
    )

    class Meta:
        db_table = "recruiter_contacts"
        ordering = ["-is_primary_contact", "name"]

    def __str__(self):
        return f"{self.name} @ {self.employer.name}"


class EmployerEngagementLog(TimestampedModel):
    """CRM interaction / engagement history log."""

    class ActivityType(models.TextChoices):
        EMAIL = "email", "Email"
        CALL = "call", "Phone Call"
        MEETING = "meeting", "In-Person Meeting"
        CAMPUS_VISIT = "campus_visit", "Campus Visit"
        EVENT = "event", "Event Participation"
        DRIVE = "drive", "Placement Drive"
        INTERNSHIP = "internship", "Internship Program"
        NOTE = "note", "Note / Follow-up"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(
        CampusEmployer, on_delete=models.CASCADE, related_name="engagement_logs"
    )
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    summary = models.TextField()
    date = models.DateField()
    logged_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employer_engagement_logs",
    )
    next_action = models.TextField(blank=True, default="")
    next_action_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "employer_engagement_logs"
        ordering = ["-date"]


class EmployerMOU(TimestampedModel):
    """MOU / formal agreement between campus and employer."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SIGNED = "signed", "Signed / Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(
        CampusEmployer, on_delete=models.CASCADE, related_name="mous"
    )
    title = models.CharField(max_length=300)
    mou_type = models.CharField(
        max_length=50,
        choices=[
            ("internship", "Internship Partnership"),
            ("placement", "Placement Partnership"),
            ("research", "Research Collaboration"),
            ("sponsorship", "Sponsorship"),
            ("general", "General MOU"),
        ],
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    document = models.FileField(upload_to="employers/mous/", null=True, blank=True)
    key_terms = models.TextField(blank=True, default="")
    annual_hire_commitment = models.PositiveSmallIntegerField(default=0)
    annual_internship_commitment = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "employer_mous"
        ordering = ["-start_date"]


class EmployerSatisfactionSurvey(TimestampedModel):
    """Employer satisfaction survey after hires/internships."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(
        CampusEmployer, on_delete=models.CASCADE, related_name="satisfaction_surveys"
    )
    respondent_name = models.CharField(max_length=200, blank=True, default="")
    survey_year = models.PositiveSmallIntegerField()
    overall_rating = models.PositiveSmallIntegerField(help_text="1–5 rating")
    candidate_quality_rating = models.PositiveSmallIntegerField(default=3)
    campus_process_rating = models.PositiveSmallIntegerField(default=3)
    would_return = models.BooleanField(null=True, blank=True)
    feedback = models.TextField(blank=True, default="")

    class Meta:
        db_table = "employer_satisfaction_surveys"
        ordering = ["-survey_year"]
