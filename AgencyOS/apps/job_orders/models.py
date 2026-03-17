"""
Job Orders app models.
Full job-order intake: staffing type, bill/pay structure, markup, SLA,
compliance requirements, approval workflow, versioning.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class JobOrder(models.Model):
    """
    A job order from a client. This is the primary work-intake record for
    an agency - richer than AgencyJobOrder in agencies app.
    """

    class StaffingType(models.TextChoices):
        PERM = "perm", "Permanent"
        CONTRACT = "contract", "Contract"
        TEMP = "temp", "Temporary"
        TEMP_TO_PERM = "temp_to_perm", "Temp to Perm"
        RETAINED = "retained", "Retained Search"
        EXECUTIVE = "executive", "Executive Search"
        PROJECT = "project", "Project-Based"
        INTERIM = "interim", "Interim Management"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        FILLED = "filled", "Filled"
        PARTIAL_FILL = "partial_fill", "Partially Filled"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"
        CRITICAL = "critical", "Critical"

    class ExclusivityType(models.TextChoices):
        CONTINGENCY = "contingency", "Contingency (Non-exclusive)"
        EXCLUSIVE = "exclusive", "Exclusive"
        RETAINED = "retained", "Retained"
        PREFERRED = "preferred", "Preferred Supplier"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="job_orders"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="job_orders",
    )
    # Legacy link
    legacy_job_order = models.OneToOneField(
        "agencies.AgencyJobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="extended_job_order",
    )
    title = models.CharField(max_length=255)
    internal_ref = models.CharField(max_length=100, blank=True)
    client_ref = models.CharField(max_length=100, blank=True)
    staffing_type = models.CharField(
        max_length=20, choices=StaffingType.choices, default=StaffingType.PERM
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    exclusivity = models.CharField(
        max_length=20, choices=ExclusivityType.choices, default=ExclusivityType.CONTINGENCY
    )
    # Staffing numbers
    positions_count = models.IntegerField(default=1)
    filled_count = models.IntegerField(default=0)
    submittal_limit = models.IntegerField(default=10)  # max candidates to submit
    # Work details
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    required_skills = models.JSONField(default=list)
    preferred_skills = models.JSONField(default=list)
    credential_requirements = models.JSONField(default=list)
    compliance_requirements = models.JSONField(default=list)
    # Location
    location_city = models.CharField(max_length=100, blank=True)
    location_country = models.CharField(max_length=100, blank=True)
    is_remote = models.BooleanField(default=False)
    is_hybrid = models.BooleanField(default=False)
    worksite_details = models.TextField(blank=True)
    # Schedule
    shift_details = models.TextField(blank=True)
    hours_per_week = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    # Commercial
    currency = models.CharField(max_length=10, default="USD")
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bill_rate_hourly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pay_rate_hourly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    markup_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    gross_margin_preview = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Fee / guarantee
    perm_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    guarantee_days = models.IntegerField(default=90)
    replacement_policy = models.TextField(blank=True)
    # Contacts
    hiring_manager_name = models.CharField(max_length=200, blank=True)
    hiring_manager_email = models.EmailField(blank=True)
    hiring_manager_contact = models.ForeignKey(
        "agency_crm.ClientContact",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="job_orders_as_hm",
    )
    # Team
    assigned_recruiter = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_job_orders",
    )
    account_manager = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="am_job_orders",
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_job_orders",
    )
    # Subcontractor allowances
    subcontractor_allowed = models.BooleanField(default=False)
    # SLA
    target_submit_date = models.DateField(null=True, blank=True)
    target_fill_date = models.DateField(null=True, blank=True)
    sla_days_to_submit = models.IntegerField(null=True, blank=True)
    sla_days_to_fill = models.IntegerField(null=True, blank=True)
    # Packaging
    candidate_packaging_notes = models.TextField(blank=True)
    intake_checklist = models.JSONField(default=dict)
    intake_completed = models.BooleanField(default=False)
    # Approval
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_job_orders",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates"
    )
    is_clone = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jo_job_order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}] – {self.agency.name}"


class JobOrderNote(models.Model):
    """Internal notes on a job order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_order = models.ForeignKey(JobOrder, on_delete=models.CASCADE, related_name="notes_set")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="jo_notes")
    body = models.TextField()
    is_internal = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jo_job_order_note"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note on {self.job_order.title} by {self.author.get_full_name()}"


class JobOrderStatusHistory(models.Model):
    """Audit trail of status changes on a job order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_order = models.ForeignKey(
        JobOrder, on_delete=models.CASCADE, related_name="status_history"
    )
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="jo_status_changes"
    )
    reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jo_status_history"
        ordering = ["-changed_at"]
