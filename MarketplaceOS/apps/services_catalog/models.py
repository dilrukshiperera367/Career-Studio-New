"""
MarketplaceOS — apps.services_catalog

Service Catalog — the product catalog of the marketplace.

Models:
    ServiceCategory     — Hierarchical service category (coaching, mentoring, etc.)
    Service             — Individual service listing by a provider
    ServicePackage      — Bundle of sessions at a packaged price
    ServiceAddOn        — Optional add-ons for a service
    ServiceSubscriptionPlan — Recurring subscription offering for a service
"""
import uuid
from django.db import models
from django.conf import settings


# ---------------------------------------------------------------------------
# Service Category
# ---------------------------------------------------------------------------

class ServiceCategory(models.Model):
    """Hierarchical category for marketplace services."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="")
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children",
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    meta_title = models.CharField(max_length=200, blank=True, default="")
    meta_description = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        db_table = "mp_service_category"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class Service(models.Model):
    """
    Individual service listing offered by a provider.
    Covers 1:1 sessions, async reviews, group sessions, and everything in between.
    """

    class ServiceType(models.TextChoices):
        MENTORING_SESSION = "mentoring_session", "1:1 Mentoring Session"
        CAREER_COACHING = "career_coaching", "Career Coaching Session"
        MOCK_INTERVIEW = "mock_interview", "Mock Interview"
        RESUME_REVIEW = "resume_review", "Resume Review"
        LINKEDIN_REVIEW = "linkedin_review", "LinkedIn Profile Review"
        COVER_LETTER_REVIEW = "cover_letter_review", "Cover Letter Review"
        PORTFOLIO_REVIEW = "portfolio_review", "Portfolio Review"
        SALARY_NEGOTIATION = "salary_negotiation", "Salary Negotiation Session"
        JOB_SEARCH_STRATEGY = "job_search_strategy", "Job Search Strategy Session"
        TECHNICAL_INTERVIEW = "technical_interview", "Technical Interview Practice"
        LEADERSHIP_COACHING = "leadership_coaching", "Leadership Coaching"
        SOFT_SKILLS_COACHING = "soft_skills_coaching", "Soft-Skills Coaching"
        LEARNING_COURSE = "learning_course", "Learning / Course Package"
        CERTIFICATION_PREP = "certification_prep", "Certification Prep"
        COHORT_PROGRAM = "cohort_program", "Cohort Program"
        WORKSHOP = "workshop", "Workshop / Webinar"
        EMPLOYER_TRAINING = "employer_training", "Employer Training Package"
        ASSESSMENT_PACKAGE = "assessment_package", "Assessment Package"

    class DeliveryMode(models.TextChoices):
        VIDEO = "video", "Live Video"
        AUDIO = "audio", "Audio Call"
        CHAT = "chat", "Chat"
        ASYNC = "async", "Async Written Review"
        GROUP = "group", "Group / Cohort Session"
        IN_PERSON = "in_person", "In Person"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private (Link Only)"
        ENTERPRISE_ONLY = "enterprise_only", "Enterprise Clients Only"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="services",
    )
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.SET_NULL, null=True,
        related_name="services",
    )
    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True, default="")
    delivery_mode = models.CharField(max_length=15, choices=DeliveryMode.choices, default=DeliveryMode.VIDEO)
    duration_minutes = models.IntegerField(default=60)

    # Pricing
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, default="LKR")
    is_free = models.BooleanField(default=False)
    compare_at_price_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Original price before discount — shown as struck-through.",
    )

    # Async turnaround
    turnaround_hours = models.IntegerField(
        null=True, blank=True,
        help_text="Turnaround time in hours for async services.",
    )

    # Discoverability
    tags = models.JSONField(default=list)
    skills_covered = models.JSONField(default=list)
    target_experience_levels = models.JSONField(
        default=list,
        help_text="e.g. ['entry', 'mid', 'senior']",
    )
    target_roles = models.JSONField(default=list)
    industries = models.JSONField(default=list)
    languages = models.JSONField(default=list)

    # Outcomes
    outcomes = models.JSONField(default=list, help_text="What the buyer gets.")
    deliverables = models.JSONField(default=list)

    # Rules
    cancellation_policy = models.TextField(blank=True, default="")
    reschedule_policy = models.TextField(blank=True, default="")
    eligibility_rules = models.TextField(blank=True, default="")
    max_sessions_per_client = models.IntegerField(
        null=True, blank=True,
        help_text="Optional cap on repeat bookings.",
    )

    # Discovery & merchandising
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    # Stats
    total_bookings = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_service"
        ordering = ["-is_featured", "-total_bookings"]
        unique_together = ["provider", "slug"]

    def __str__(self):
        return f"{self.title} — {self.provider.display_name}"


# ---------------------------------------------------------------------------
# Service Package / Bundle
# ---------------------------------------------------------------------------

class ServicePackage(models.Model):
    """
    Bundle of multiple sessions sold at a packaged (usually discounted) price.
    e.g. "5 mock interviews for LKR 8,000"
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=400, blank=True, default="")
    session_count = models.IntegerField(default=1)
    validity_days = models.IntegerField(
        default=90,
        help_text="Number of days from purchase within which sessions must be used.",
    )
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    per_session_price_lkr = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Effective per-session price for display.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_service_package"
        ordering = ["sort_order", "session_count"]

    def __str__(self):
        return f"{self.service.title} — {self.name} ({self.session_count} sessions)"


# ---------------------------------------------------------------------------
# Service Add-On
# ---------------------------------------------------------------------------

class ServiceAddOn(models.Model):
    """Optional add-on that can be attached to a service booking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="addons")
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=300, blank=True, default="")
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mp_service_addon"

    def __str__(self):
        return f"{self.service.title} + {self.name}"


# ---------------------------------------------------------------------------
# Saved Service / Saved Provider (buyer bookmarks)
# ---------------------------------------------------------------------------

class SavedProvider(models.Model):
    """Buyer's saved / bookmarked provider."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_providers",
    )
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="saved_by",
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_saved_provider"
        unique_together = ["user", "provider"]

    def __str__(self):
        return f"{self.user.email} saved {self.provider.display_name}"


class SavedService(models.Model):
    """Buyer's saved / bookmarked service."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_services",
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="saved_by",
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_saved_service"
        unique_together = ["user", "service"]

    def __str__(self):
        return f"{self.user.email} saved {self.service.title}"
