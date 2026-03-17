"""AgencyOS — staffing firms, RPOs, recruiting agencies.

Models:
    Agency            — Staffing firm / RPO / recruiting agency
    AgencyClient      — Employer client with contract terms
    AgencyRecruiter   — Recruiter seat within an agency
    AgencyJobOrder    — Open role/job order from a client
    AgencySubmission  — Candidate submitted to a client job
    AgencyPlacement   — Confirmed placement with fee tracking
    AgencyContractor  — Contractor in the agency pool
    TalentPool        — Cross-client talent pool
"""
import uuid
from django.db import models
from django.conf import settings


# ── Agency Profile ──────────────────────────────────────────────────────────

class Agency(models.Model):
    """Staffing firm / RPO / recruiting agency."""

    class Tier(models.TextChoices):
        STANDARD = "standard", "Standard"
        PREFERRED = "preferred", "Preferred"
        ELITE = "elite", "Elite"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    logo_url = models.URLField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    industry_focus = models.JSONField(default=list, blank=True, help_text="Industries served")
    description = models.TextField(blank=True, default="")
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.STANDARD)
    is_verified = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="owned_agencies"
    )
    # Contact
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    address = models.TextField(blank=True, default="")
    country = models.CharField(max_length=100, default="Sri Lanka")
    # Stats (denormalized for performance)
    total_placements = models.IntegerField(default=0)
    active_recruiters = models.IntegerField(default=0)
    active_clients = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_agency"
        verbose_name_plural = "Agencies"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ── Agency-Client Relationship ───────────────────────────────────────────────

class AgencyClient(models.Model):
    """Employer client of an agency with contract terms."""

    class FeeType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage of Salary"
        FLAT = "flat", "Flat Fee"
        RETAINER = "retainer", "Retainer"
        HOURLY = "hourly", "Hourly Markup"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        TERMINATED = "terminated", "Terminated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="clients")
    # Cross-portal employer reference (stored as denormalized data)
    employer_name = models.CharField(max_length=300)
    employer_ref = models.CharField(max_length=200, blank=True, default="", help_text="External employer ID/slug")
    employer_contact_email = models.EmailField(blank=True, default="")
    employer_contact_name = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    fee_type = models.CharField(max_length=20, choices=FeeType.choices, default=FeeType.PERCENTAGE)
    fee_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    guarantee_days = models.IntegerField(default=90, help_text="Placement guarantee period (days)")
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_client"
        unique_together = ["agency", "employer_ref"]
        ordering = ["employer_name"]

    def __str__(self):
        return f"{self.agency.name} → {self.employer_name}"


# ── Agency Recruiters ────────────────────────────────────────────────────────

class AgencyRecruiter(models.Model):
    """Recruiter seat within an agency."""

    class Role(models.TextChoices):
        OWNER = "owner", "Agency Owner"
        MANAGER = "manager", "Team Manager"
        RECRUITER = "recruiter", "Recruiter"
        RESEARCHER = "researcher", "Researcher"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="recruiters")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="agency_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECRUITER)
    is_active = models.BooleanField(default=True)
    desk = models.CharField(max_length=200, blank=True, default="", help_text="Recruiter desk/specialty")
    assigned_clients = models.ManyToManyField(AgencyClient, blank=True, related_name="assigned_recruiters")
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_recruiter"
        unique_together = ["agency", "user"]

    def __str__(self):
        return f"{self.user} @ {self.agency.name} ({self.get_role_display()})"


# ── Job Orders ───────────────────────────────────────────────────────────────

class AgencyJobOrder(models.Model):
    """Open role / job order from a client."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        FILLED = "filled", "Filled"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="agency_job_orders")
    client = models.ForeignKey(AgencyClient, on_delete=models.CASCADE, related_name="agency_job_orders")
    assigned_recruiter = models.ForeignKey(
        AgencyRecruiter, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="job_orders"
    )
    title = models.CharField(max_length=400)
    description = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    location = models.CharField(max_length=300, blank=True, default="")
    is_remote = models.BooleanField(default=False)
    employment_type = models.CharField(max_length=50, default="full_time")
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, default="LKR")
    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    # Cross-portal reference
    external_job_ref = models.CharField(max_length=200, blank=True, default="")
    positions_count = models.IntegerField(default=1)
    filled_count = models.IntegerField(default=0)
    target_fill_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_job_order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.client.employer_name}"


# ── Candidate Submissions ────────────────────────────────────────────────────

class AgencySubmission(models.Model):
    """Agency submitting a candidate for a client job order."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Client Reviewed"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer Stage"
        PLACED = "placed", "Placed"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="agency_submissions")
    recruiter = models.ForeignKey(
        AgencyRecruiter, on_delete=models.SET_NULL, null=True, related_name="agency_submission_set"
    )
    client = models.ForeignKey(AgencyClient, on_delete=models.CASCADE, related_name="agency_client_submissions")
    job_order = models.ForeignKey(AgencyJobOrder, on_delete=models.CASCADE, related_name="agency_job_submissions")
    # Candidate info (cross-portal reference + denormalized)
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="agency_submissions"
    )
    candidate_name = models.CharField(max_length=300, blank=True, default="")
    candidate_email = models.EmailField(blank=True, default="")
    candidate_ref = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    cover_note = models.TextField(blank=True, default="")
    resume_url = models.URLField(blank=True, default="")
    match_score = models.FloatField(null=True, blank=True)
    # Ownership window
    ownership_start = models.DateTimeField(auto_now_add=True)
    ownership_expires = models.DateTimeField(null=True, blank=True)
    # Timeline
    client_reviewed_at = models.DateTimeField(null=True, blank=True)
    interview_scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_submission"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.candidate_name or self.candidate} → {self.job_order.title}"


# ── Placements ───────────────────────────────────────────────────────────────

class AgencyPlacement(models.Model):
    """Confirmed placement with fee and margin tracking."""

    class PlacementType(models.TextChoices):
        PERMANENT = "permanent", "Permanent"
        CONTRACT = "contract", "Contract"
        TEMP_TO_PERM = "temp_to_perm", "Temp-to-Perm"
        TEMP = "temp", "Temporary"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.OneToOneField(
        AgencySubmission, on_delete=models.CASCADE, related_name="placement"
    )
    placement_type = models.CharField(
        max_length=20, choices=PlacementType.choices, default=PlacementType.PERMANENT
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, default="LKR")
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fee_paid = models.BooleanField(default=False)
    fee_paid_at = models.DateTimeField(null=True, blank=True)
    margin_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    guarantee_end = models.DateField(null=True, blank=True)
    replacement_requested = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_placement"
        ordering = ["-start_date"]

    def __str__(self):
        return f"Placement: {self.submission.candidate_name} @ {self.submission.job_order.title}"


# ── Contractor Pool ───────────────────────────────────────────────────────────

class AgencyContractor(models.Model):
    """Contractor in the agency's pool, redeployable across clients."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ON_ASSIGNMENT = "on_assignment", "On Assignment"
        UNAVAILABLE = "unavailable", "Unavailable"
        OFFBOARDED = "offboarded", "Offboarded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="contractors")
    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="contractor_profiles"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    current_client = models.ForeignKey(
        AgencyClient, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_contractors"
    )
    day_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, default="LKR")
    assignment_start = models.DateField(null=True, blank=True)
    assignment_end = models.DateField(null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    extension_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_contractor"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.person} — {self.get_status_display()}"


# ── Cross-Client Talent Pool ──────────────────────────────────────────────────

class TalentPool(models.Model):
    """Curated talent pool maintained by an agency."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="talent_pools")
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="talent_pools",
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_talent_pools"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agency_talent_pool"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.agency.name})"
