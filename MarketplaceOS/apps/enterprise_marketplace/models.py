"""
MarketplaceOS — apps.enterprise_marketplace

Enterprise Marketplace / B2B Layer.

Enables companies (TalentOS/WorkforceOS/CampusOS customers) to:
  - set team coaching budgets
  - approve providers for their employees
  - allocate credits to team members
  - manage sponsored bookings and invoicing
  - run a private internal mentor marketplace

Models:
    EnterpriseAccount       — Company/employer account on the marketplace
    EnterpriseTeamMember    — Employee linked to an enterprise account
    EnterpriseBudget        — Coaching/learning budget pool for a company
    EnterpriseBudgetAlloc   — Per-employee budget allocation
    EnterpriseApprovedProvider — Company's approved provider list
    EnterpriseCatalogItem   — Company-specific private service listing
    EnterpriseBookingApproval  — Manager approval workflow for bookings
    EnterpriseInvoice       — Consolidated company invoice
    InternalMentorProgram   — Internal mentor marketplace for WorkforceOS
    InternalMentorMatch     — Match record between internal mentor and mentee
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class EnterpriseAccount(models.Model):
    """
    Company/employer account on MarketplaceOS.
    Linked to TalentOS or WorkforceOS customer accounts.
    """

    class AccountStatus(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        EXPIRED = "expired", "Expired"

    class AccountTier(models.TextChoices):
        STARTER = "starter", "Starter"
        GROWTH = "growth", "Growth"
        ENTERPRISE = "enterprise", "Enterprise"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=150, unique=True)
    industry = models.CharField(max_length=100, blank=True, default="")
    company_size = models.CharField(max_length=30, blank=True, default="",
                                     help_text="e.g. 1-10, 11-50, 51-200, 201-1000, 1000+")
    primary_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_enterprises",
    )
    status = models.CharField(max_length=15, choices=AccountStatus.choices, default=AccountStatus.TRIAL)
    tier = models.CharField(max_length=15, choices=AccountTier.choices, default=AccountTier.STARTER)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    billing_email = models.EmailField(blank=True, default="")
    billing_address = models.TextField(blank=True, default="")
    vat_number = models.CharField(max_length=50, blank=True, default="")
    custom_pricing_notes = models.TextField(blank=True, default="")
    has_private_marketplace = models.BooleanField(default=False)
    allowed_provider_types = models.JSONField(
        default=list, help_text="Restrict employees to specific provider types.",
    )
    max_seats = models.IntegerField(default=0, help_text="0 = unlimited seats.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_enterprise_account"
        ordering = ["company_name"]

    def __str__(self):
        return f"{self.company_name} ({self.tier})"


class EnterpriseTeamMember(models.Model):
    """Employee linked to an enterprise account."""

    class MemberRole(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Company Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enterprise = models.ForeignKey(EnterpriseAccount, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enterprise_memberships")
    role = models.CharField(max_length=15, choices=MemberRole.choices, default=MemberRole.EMPLOYEE)
    department = models.CharField(max_length=100, blank=True, default="")
    cost_center = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_enterprise_member"
        unique_together = [["enterprise", "user"]]

    def __str__(self):
        return f"{self.user.email} @ {self.enterprise.company_name} ({self.role})"


class EnterpriseBudget(models.Model):
    """Employer-sponsored coaching/learning budget pool."""

    class BudgetType(models.TextChoices):
        COACHING = "coaching", "Coaching & Mentoring"
        LEARNING = "learning", "Learning & Development"
        ASSESSMENT = "assessment", "Assessments"
        GENERAL = "general", "General Marketplace"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enterprise = models.ForeignKey(EnterpriseAccount, on_delete=models.CASCADE, related_name="budgets")
    name = models.CharField(max_length=200, help_text="e.g. Q1 2025 Coaching Budget")
    budget_type = models.CharField(max_length=15, choices=BudgetType.choices, default=BudgetType.GENERAL)
    total_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    spent_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=5, default="LKR")
    per_employee_cap_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    requires_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_enterprise_budget"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.enterprise.company_name} — {self.name} ({self.total_amount_lkr} LKR)"

    @property
    def available_amount_lkr(self):
        return self.total_amount_lkr - self.spent_amount_lkr


class EnterpriseBudgetAlloc(models.Model):
    """Per-employee budget allocation from an enterprise budget."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(EnterpriseBudget, on_delete=models.CASCADE, related_name="allocations")
    member = models.ForeignKey(EnterpriseTeamMember, on_delete=models.CASCADE, related_name="budget_allocations")
    allocated_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    spent_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_enterprise_budget_alloc"
        unique_together = [["budget", "member"]]

    def __str__(self):
        return f"{self.member} — {self.allocated_lkr} LKR"


class EnterpriseApprovedProvider(models.Model):
    """Company's approved provider list — restricts or pre-approves providers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enterprise = models.ForeignKey(EnterpriseAccount, on_delete=models.CASCADE, related_name="approved_providers")
    provider = models.ForeignKey("providers.Provider", on_delete=models.CASCADE)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, default="")
    approved_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mp_enterprise_approved_provider"
        unique_together = [["enterprise", "provider"]]

    def __str__(self):
        return f"{self.enterprise.company_name} approved {self.provider.display_name}"


class EnterpriseCatalogItem(models.Model):
    """Service listing visible only to a specific enterprise's employees."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enterprise = models.ForeignKey(EnterpriseAccount, on_delete=models.CASCADE, related_name="catalog_items")
    service = models.ForeignKey("services_catalog.Service", on_delete=models.CASCADE)
    custom_price_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Company-negotiated price override.",
    )
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_enterprise_catalog_item"
        unique_together = [["enterprise", "service"]]

    def __str__(self):
        return f"{self.enterprise.company_name} — {self.service.title}"


class EnterpriseBookingApproval(models.Model):
    """Manager approval workflow for enterprise-sponsored bookings."""

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        AUTO_APPROVED = "auto_approved", "Auto-Approved (Within Budget)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField("bookings.Booking", on_delete=models.CASCADE, related_name="enterprise_approval")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="approval_decisions",
    )
    status = models.CharField(max_length=15, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    approver_notes = models.TextField(blank=True, default="")
    budget_allocation = models.ForeignKey(EnterpriseBudgetAlloc, on_delete=models.SET_NULL, null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_enterprise_booking_approval"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Approval {self.status} for {self.booking.reference}"


class InternalMentorProgram(models.Model):
    """
    Internal mentor marketplace mode for WorkforceOS customers.
    Company employees mentor other employees — managed by the enterprise account.
    """

    class ProgramStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        DRAFT = "draft", "Draft"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enterprise = models.ForeignKey(EnterpriseAccount, on_delete=models.CASCADE, related_name="mentor_programs")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    goals = models.JSONField(default=list)
    eligible_roles = models.JSONField(default=list, help_text="Job titles/roles eligible to join.")
    max_mentee_pairs = models.IntegerField(null=True, blank=True)
    duration_weeks = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=ProgramStatus.choices, default=ProgramStatus.DRAFT)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_internal_mentor_program"

    def __str__(self):
        return f"{self.enterprise.company_name} — {self.name}"


class InternalMentorMatch(models.Model):
    """Mentor-mentee pairing within an internal mentor program."""

    class MatchStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        PAUSED = "paused", "Paused"
        ENDED = "ended", "Ended Early"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(InternalMentorProgram, on_delete=models.CASCADE, related_name="matches")
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="internal_mentoring",
    )
    mentee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="internal_mentees",
    )
    goals = models.JSONField(default=list)
    status = models.CharField(max_length=15, choices=MatchStatus.choices, default=MatchStatus.ACTIVE)
    sessions_completed = models.IntegerField(default=0)
    matched_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_internal_mentor_match"
        unique_together = [["program", "mentee"]]

    def __str__(self):
        return f"{self.mentor} → {self.mentee} ({self.program.name})"
