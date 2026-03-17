"""
Contractor Operations models.
Assignment lifecycle: creation, extensions, redeployment, compliance,
credential tracking, incident logging, contractor check-ins.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Assignment(models.Model):
    """
    A contractor/temp assignment at a client site.
    Central record for the full assignment lifecycle.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Start"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        EXTENDED = "extended", "Extended"
        ENDING_SOON = "ending_soon", "Ending Soon"
        ENDED = "ended", "Ended"
        TERMINATED_EARLY = "terminated_early", "Terminated Early"
        CONVERTED = "converted", "Converted to Perm"

    class AssignmentType(models.TextChoices):
        CONTRACT = "contract", "Contract"
        TEMP = "temp", "Temporary"
        TEMP_TO_PERM = "temp_to_perm", "Temp to Perm"
        INTERIM = "interim", "Interim"
        PROJECT = "project", "Project-Based"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="assignments"
    )
    candidate = models.ForeignKey(
        "submissions.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    job_order = models.ForeignKey(
        "job_orders.JobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignments",
    )
    placement = models.OneToOneField(
        "agencies.AgencyPlacement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignment",
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignments",
    )
    assignment_type = models.CharField(
        max_length=20, choices=AssignmentType.choices, default=AssignmentType.CONTRACT
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    # Dates
    start_date = models.DateField()
    original_end_date = models.DateField(null=True, blank=True)
    current_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    # Site & supervisor
    worksite_name = models.CharField(max_length=200, blank=True)
    worksite_address = models.TextField(blank=True)
    supervisor_name = models.CharField(max_length=200, blank=True)
    supervisor_email = models.EmailField(blank=True)
    supervisor_contact = models.ForeignKey(
        "agency_crm.ClientContact",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_assignments",
    )
    # Rates
    currency = models.CharField(max_length=10, default="USD")
    pay_rate_hourly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bill_rate_hourly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    markup_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overtime_bill_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Extensions
    extension_count = models.IntegerField(default=0)
    is_conversion_eligible = models.BooleanField(default=False)
    conversion_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Admin
    assigned_recruiter = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_assignments"
    )
    notes = models.TextField(blank=True)
    early_termination_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cop_assignment"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.candidate} @ {self.client_account} [{self.get_status_display()}]"


class AssignmentExtension(models.Model):
    """A formal extension record for an assignment."""

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        PENDING_CLIENT = "pending_client", "Pending Client Approval"
        PENDING_CANDIDATE = "pending_candidate", "Pending Candidate Acceptance"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        APPLIED = "applied", "Applied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="extensions"
    )
    previous_end_date = models.DateField()
    new_end_date = models.DateField()
    new_pay_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    new_bill_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PROPOSED)
    requested_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="requested_extensions"
    )
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_extensions"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cop_extension"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Extension for {self.assignment} until {self.new_end_date}"


class ContractorDocument(models.Model):
    """Documents collected for a contractor assignment (compliance packet)."""

    class DocumentType(models.TextChoices):
        ID = "id", "Government ID"
        WORK_PERMIT = "work_permit", "Work Permit / Visa"
        CONTRACT = "contract", "Assignment Contract"
        NDA = "nda", "NDA"
        BACKGROUND_CHECK = "background_check", "Background Check"
        DRUG_SCREEN = "drug_screen", "Drug Screen"
        CERTIFICATE = "certificate", "Certificate / License"
        INSURANCE = "insurance", "Insurance Certificate"
        POLICY_ACK = "policy_ack", "Policy Acknowledgement"
        SAFETY_TRAINING = "safety_training", "Safety Training"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Collection"
        COLLECTED = "collected", "Collected"
        VERIFIED = "verified", "Verified"
        EXPIRED = "expired", "Expired"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    title = models.CharField(max_length=200)
    file_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expiry_date = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_documents"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cop_contractor_document"

    def __str__(self):
        return f"{self.get_document_type_display()} – {self.assignment}"


class AssignmentIncident(models.Model):
    """Log of incidents or issues during an assignment."""

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="incidents"
    )
    reported_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reported_incidents"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.LOW)
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cop_incident"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"


class ContractorCheckIn(models.Model):
    """Periodic check-ins with contractors during assignment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="check_ins"
    )
    checked_in_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="check_ins_done"
    )
    satisfaction_score = models.IntegerField(null=True, blank=True)  # 1-5
    notes = models.TextField(blank=True)
    action_items = models.TextField(blank=True)
    check_in_date = models.DateTimeField()
    next_check_in_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cop_check_in"
        ordering = ["-check_in_date"]
