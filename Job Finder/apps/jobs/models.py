"""Jobs app — Job listings, the core model.
Defined in Part 1 schema §5.3.
"""
import uuid
from django.db import models
from django.conf import settings


class JobListing(models.Model):
    """Main job posting model — ~60 fields across search, i18n, location,
    compensation, screening, status, promotion, ATS link, denormalized stats, SEO."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending Review"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        EXPIRED = "expired", "Expired"
        FILLED = "filled", "Filled"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        TEMPORARY = "temporary", "Temporary"
        FREELANCE = "freelance", "Freelance"

    class ExperienceLevel(models.TextChoices):
        ENTRY = "entry", "Entry Level"
        JUNIOR = "junior", "Junior"
        MID = "mid", "Mid Level"
        SENIOR = "senior", "Senior"
        LEAD = "lead", "Lead"
        EXECUTIVE = "executive", "Executive"

    class WorkArrangement(models.TextChoices):
        ONSITE = "onsite", "On-site"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"
        FLEXIBLE = "flexible", "Flexible"

    class SalaryCurrency(models.TextChoices):
        LKR = "LKR", "Sri Lankan Rupee"
        USD = "USD", "US Dollar"
        EUR = "EUR", "Euro"
        GBP = "GBP", "British Pound"
        AED = "AED", "Emirati Dirham"
        SAR = "SAR", "Saudi Riyal"
        QAR = "QAR", "Qatari Riyal"
        SGD = "SGD", "Singapore Dollar"

    class ApplyMethod(models.TextChoices):
        INTERNAL = "internal", "In-Platform"
        EXTERNAL_URL = "external_url", "External URL"
        EMAIL = "email", "Email"
        ATS = "ats", "ATS System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=300, unique=True)

    # Employer
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="jobs")
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="posted_jobs")

    # Trilingual content
    title = models.CharField(max_length=200)
    title_si = models.CharField(max_length=200, blank=True, default="")
    title_ta = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField()
    description_si = models.TextField(blank=True, default="")
    description_ta = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    requirements_si = models.TextField(blank=True, default="")
    requirements_ta = models.TextField(blank=True, default="")
    benefits = models.TextField(blank=True, default="")
    benefits_si = models.TextField(blank=True, default="")
    benefits_ta = models.TextField(blank=True, default="")

    # Classification
    category = models.ForeignKey("taxonomy.JobCategory", on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs")
    subcategory = models.ForeignKey("taxonomy.JobSubCategory", on_delete=models.SET_NULL, null=True, blank=True)
    industry = models.ForeignKey("taxonomy.Industry", on_delete=models.SET_NULL, null=True, blank=True)
    job_type = models.CharField(max_length=10, choices=JobType.choices)
    experience_level = models.CharField(max_length=10, choices=ExperienceLevel.choices, blank=True, default="")
    work_arrangement = models.CharField(max_length=10, choices=WorkArrangement.choices, default=WorkArrangement.ONSITE)

    # Location
    province = models.ForeignKey("taxonomy.Province", on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    address_line = models.CharField(max_length=300, blank=True, default="")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # Compensation
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, choices=SalaryCurrency.choices, default=SalaryCurrency.LKR)
    salary_period = models.CharField(max_length=10, choices=[("hourly", "Hourly"), ("monthly", "Monthly"), ("annual", "Annual")], default="monthly")
    hide_salary = models.BooleanField(default=False)

    # Skills
    required_skills = models.ManyToManyField("taxonomy.Skill", blank=True, related_name="required_for_jobs")
    preferred_skills = models.ManyToManyField("taxonomy.Skill", blank=True, related_name="preferred_for_jobs")
    min_education = models.ForeignKey("taxonomy.EducationLevel", on_delete=models.SET_NULL, null=True, blank=True)
    experience_years_min = models.IntegerField(null=True, blank=True)
    experience_years_max = models.IntegerField(null=True, blank=True)

    # Screening questions
    screening_questions = models.JSONField(default=list, blank=True)
    requires_cover_letter = models.BooleanField(default=False)
    requires_resume = models.BooleanField(default=True)

    # Application method
    apply_method = models.CharField(max_length=15, choices=ApplyMethod.choices, default=ApplyMethod.INTERNAL)
    external_apply_url = models.URLField(max_length=500, blank=True, default="")
    email_apply_address = models.EmailField(blank=True, default="")

    # Status & dates
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    featured_until = models.DateTimeField(null=True, blank=True)
    urgent = models.BooleanField(default=False)

    # Promotion / boost
    is_featured = models.BooleanField(default=False)
    is_boosted = models.BooleanField(default=False)
    boost_factor = models.FloatField(default=1.0)
    is_sponsored = models.BooleanField(default=False, help_text="Linked to a PromotedJobCampaign")

    # Quick Apply & Application Deadline
    quick_apply_enabled = models.BooleanField(default=False, help_text="Allow one-click apply with saved profile")
    application_deadline = models.DateField(null=True, blank=True, help_text="Display deadline for applications")

    # Quality & Freshness (computed by job_quality app)
    quality_score = models.FloatField(default=0.0, help_text="0–100 overall quality score")
    freshness_score = models.FloatField(default=0.0, help_text="0–100 freshness score")

    # Extras & Enrichment
    visa_sponsorship = models.BooleanField(default=False, help_text="Job offers visa sponsorship")
    shift_type = models.CharField(
        max_length=15,
        choices=[("day", "Day Shift"), ("night", "Night Shift"), ("rotating", "Rotating"), ("flexible", "Flexible")],
        blank=True, default="",
    )
    language_requirements = models.JSONField(
        default=list, blank=True,
        help_text="e.g. [{\"language\": \"English\", \"level\": \"proficient\"}]"
    )
    structured_faqs = models.JSONField(
        default=list, blank=True,
        help_text="e.g. [{\"question\": \"\", \"answer\": \"\"}]"
    )

    # ATS link
    ats_job_id = models.CharField(max_length=100, blank=True, default="")
    ats_pipeline_id = models.CharField(max_length=100, blank=True, default="")
    ats_synced_at = models.DateTimeField(null=True, blank=True)

    # Denormalized stats
    view_count = models.IntegerField(default=0)
    application_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)

    # SEO
    meta_title = models.CharField(max_length=70, blank=True, default="")
    meta_description = models.CharField(max_length=160, blank=True, default="")
    canonical_url = models.URLField(max_length=500, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_job_listings"
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="idx_job_status_pub"),
            models.Index(fields=["employer", "status"], name="idx_job_employer_status"),
            models.Index(fields=["category", "status"], name="idx_job_cat_status"),
            models.Index(fields=["district", "status"], name="idx_job_district_status"),
            models.Index(fields=["job_type", "status"], name="idx_job_type_status"),
            models.Index(fields=["experience_level", "status"], name="idx_job_exp_status"),
            models.Index(fields=["slug"], name="idx_job_slug"),
        ]

    def __str__(self):
        return f"{self.title} — {self.employer}"


class SavedJob(models.Model):
    """Seekers can save/bookmark jobs."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_jobs")
    job = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name="saves")
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "jf_saved_jobs"
        unique_together = ["user", "job"]


class JobView(models.Model):
    """Track individual job pageviews for analytics."""
    job = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=64, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referrer = models.CharField(max_length=500, blank=True, default="")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_job_views"
