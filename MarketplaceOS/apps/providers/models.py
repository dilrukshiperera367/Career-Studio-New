"""
MarketplaceOS — apps.providers

Provider / Expert Onboarding — the supply side of the marketplace.

Models:
    Provider            — Expert profile (mentor, coach, mock interviewer, etc.)
    ProviderCredential  — Verified credential / certification
    ProviderAvailabilitySlot — Weekly recurring availability
    ProviderBlackout    — Blocked dates / unavailable periods
    ProviderBadge       — Platform-awarded trust & quality badges
    ProviderApplication — Onboarding application flow
    ProviderContract    — Terms acceptance record
"""
import uuid
from django.db import models
from django.conf import settings


# ---------------------------------------------------------------------------
# Provider — core profile
# ---------------------------------------------------------------------------

class Provider(models.Model):
    """
    Expert / service-provider profile on MarketplaceOS.
    Covers mentors, career coaches, mock interviewers, LinkedIn reviewers,
    resume reviewers, salary negotiation coaches, corporate trainers,
    learning providers, certification partners, assessment providers,
    agency partners, campus partners, and internal mentors.
    """

    class ProviderType(models.TextChoices):
        MENTOR = "mentor", "Mentor"
        CAREER_COACH = "career_coach", "Career Coach"
        MOCK_INTERVIEWER = "mock_interviewer", "Mock Interviewer"
        RESUME_REVIEWER = "resume_reviewer", "Resume / CV Reviewer"
        LINKEDIN_REVIEWER = "linkedin_reviewer", "LinkedIn Profile Reviewer"
        COVER_LETTER_REVIEWER = "cover_letter_reviewer", "Cover Letter Reviewer"
        SALARY_NEGOTIATION_COACH = "salary_negotiation_coach", "Salary Negotiation Coach"
        LEARNING_PROVIDER = "learning_provider", "Learning / Course Provider"
        CERTIFICATION_PARTNER = "certification_partner", "Certification Partner"
        ASSESSMENT_PROVIDER = "assessment_provider", "Assessment Provider"
        AGENCY_PARTNER = "agency_partner", "Agency Partner"
        CAMPUS_PARTNER = "campus_partner", "Campus / University Partner"
        CORPORATE_TRAINER = "corporate_trainer", "Corporate Trainer"
        INTERNAL_MENTOR = "internal_mentor", "Internal Mentor (WorkforceOS)"
        LEADERSHIP_COACH = "leadership_coach", "Leadership Coach"
        SOFT_SKILLS_COACH = "soft_skills_coach", "Soft-Skills Coach"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        SUSPENDED = "suspended", "Suspended"
        ARCHIVED = "archived", "Archived"

    class DeliveryMode(models.TextChoices):
        VIDEO = "video", "Video Call"
        AUDIO = "audio", "Audio Call"
        CHAT = "chat", "Chat"
        ASYNC = "async", "Async / Written Review"
        GROUP = "group", "Group / Cohort Session"
        IN_PERSON = "in_person", "In Person"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_profile",
    )
    slug = models.SlugField(max_length=200, unique=True)
    provider_type = models.CharField(max_length=30, choices=ProviderType.choices)
    secondary_types = models.JSONField(
        default=list, blank=True,
        help_text="Additional provider types beyond primary.",
    )
    display_name = models.CharField(max_length=200)
    headline = models.CharField(max_length=300, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    profile_photo_url = models.URLField(blank=True, default="")
    intro_video_url = models.URLField(blank=True, default="")
    portfolio_url = models.URLField(blank=True, default="")
    website_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")

    # Expertise
    expertise_categories = models.JSONField(default=list, help_text="Category slugs.")
    skills = models.JSONField(default=list, help_text="Skill tags.")
    industries = models.JSONField(default=list, help_text="Industries served.")
    target_roles = models.JSONField(default=list, help_text="Job roles this provider helps with.")
    experience_years = models.IntegerField(default=0)
    current_role = models.CharField(max_length=200, blank=True, default="")
    current_company = models.CharField(max_length=200, blank=True, default="")
    education = models.JSONField(default=list, help_text="Degrees/certs list.")

    # Delivery
    delivery_modes = models.JSONField(default=list, help_text="Supported delivery modes.")
    languages = models.JSONField(default=list, help_text="Languages spoken.")
    timezone = models.CharField(max_length=50, default="Asia/Colombo")
    country = models.CharField(max_length=100, default="Sri Lanka")
    city = models.CharField(max_length=100, blank=True, default="")

    # Pricing
    base_rate_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Base rate per session in LKR.",
    )
    currency = models.CharField(max_length=5, default="LKR")

    # Payout
    payout_method = models.CharField(max_length=50, blank=True, default="")
    payout_account_ref = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Encrypted payout account reference.",
    )
    kyc_completed = models.BooleanField(default=False)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)

    # Trust & quality
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_enterprise_approved = models.BooleanField(default=False)
    trust_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    response_time_hours = models.DecimalField(max_digits=5, decimal_places=1, default=24)

    # Denormalized stats (updated via signals)
    total_sessions = models.IntegerField(default=0)
    total_reviews = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    repeat_booking_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Operational
    profile_completion_pct = models.IntegerField(default=0)
    contract_accepted_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspension_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_provider"
        ordering = ["-trust_score", "-average_rating"]

    def __str__(self):
        return f"{self.display_name} ({self.get_provider_type_display()})"


# ---------------------------------------------------------------------------
# Provider Credential
# ---------------------------------------------------------------------------

class ProviderCredential(models.Model):
    """Verified credential, certification, or work experience record."""

    class CredentialType(models.TextChoices):
        DEGREE = "degree", "Academic Degree"
        CERTIFICATION = "certification", "Professional Certification"
        WORK_EXPERIENCE = "work_experience", "Work Experience"
        AWARD = "award", "Award / Recognition"
        PUBLICATION = "publication", "Publication"
        SPEAKING = "speaking", "Speaking Engagement"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="credentials",
    )
    credential_type = models.CharField(max_length=20, choices=CredentialType.choices)
    title = models.CharField(max_length=300)
    issuing_organization = models.CharField(max_length=300, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_url = models.URLField(blank=True, default="")
    document_url = models.URLField(blank=True, default="")
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_provider_credential"
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.provider.display_name} — {self.title}"


# ---------------------------------------------------------------------------
# Provider Availability
# ---------------------------------------------------------------------------

class ProviderAvailabilitySlot(models.Model):
    """
    Weekly recurring availability slot for a provider.
    Stored as day-of-week + start/end time for timezone-aware calendar rendering.
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="availability_slots",
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mp_provider_availability"
        ordering = ["day_of_week", "start_time"]

    def __str__(self):
        return (
            f"{self.provider.display_name} — "
            f"{self.get_day_of_week_display()} {self.start_time}–{self.end_time}"
        )


class ProviderBlackout(models.Model):
    """Date range during which the provider is unavailable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="blackouts",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "mp_provider_blackout"
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.provider.display_name} unavailable {self.start_date}–{self.end_date}"


# ---------------------------------------------------------------------------
# Provider Badges
# ---------------------------------------------------------------------------

class ProviderBadge(models.Model):
    """
    Trust and quality badge awarded to a provider.
    Badge types: Verified, Top Rated, Fast Response, Enterprise Approved, Rising Star.
    """

    class BadgeType(models.TextChoices):
        VERIFIED = "verified", "Verified"
        TOP_RATED = "top_rated", "Top Rated"
        FAST_RESPONSE = "fast_response", "Fast Response"
        ENTERPRISE_APPROVED = "enterprise_approved", "Enterprise Approved"
        RISING_STAR = "rising_star", "Rising Star"
        EXPERT_MENTOR = "expert_mentor", "Expert Mentor"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="badges",
    )
    badge_type = models.CharField(max_length=25, choices=BadgeType.choices)
    awarded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mp_provider_badge"
        unique_together = ["provider", "badge_type"]

    def __str__(self):
        return f"{self.provider.display_name} — {self.get_badge_type_display()}"


# ---------------------------------------------------------------------------
# Provider Application (onboarding flow)
# ---------------------------------------------------------------------------

class ProviderApplication(models.Model):
    """Tracks the provider onboarding application and moderation workflow."""

    class ApplicationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        INFO_REQUESTED = "info_requested", "More Information Requested"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.OneToOneField(
        Provider, on_delete=models.CASCADE, related_name="application",
    )
    status = models.CharField(
        max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.DRAFT,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reviewed_applications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    admin_notes = models.TextField(blank=True, default="")
    identity_verified = models.BooleanField(default=False)
    credentials_verified = models.BooleanField(default=False)
    background_check_passed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_provider_application"

    def __str__(self):
        return f"Application: {self.provider.display_name} ({self.status})"


# ---------------------------------------------------------------------------
# Provider Contract
# ---------------------------------------------------------------------------

class ProviderContract(models.Model):
    """Records provider's acceptance of platform terms and service agreement."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="contracts",
    )
    contract_version = models.CharField(max_length=20)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        db_table = "mp_provider_contract"
        ordering = ["-accepted_at"]

    def __str__(self):
        return f"{self.provider.display_name} — v{self.contract_version}"
