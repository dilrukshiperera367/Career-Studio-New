"""Internal Recruiting app — Internal mobility, transfers, and internal vs external hiring decisions."""

import uuid
from django.db import models


class InternalPostingWindow(models.Model):
    """A time window during which a job is exclusively open to internal candidates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_posting_windows")
    job = models.OneToOneField(
        "jobs.Job", on_delete=models.CASCADE, related_name="internal_posting_window"
    )
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    is_exclusive = models.BooleanField(
        default=True, help_text="If True, external candidates cannot apply until window closes"
    )
    notify_employees = models.BooleanField(default=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "internal_posting_windows"

    def __str__(self):
        return f"Internal window for {self.job.title}"


class InternalRequisition(models.Model):
    """An internal job requisition raised by a manager for an internal fill."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("on_hold", "On Hold"),
        ("filled", "Filled"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_requisitions")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, null=True, blank=True, related_name="internal_requisitions"
    )
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=150, blank=True, default="")
    hiring_manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="internal_requisitions_managed"
    )
    recruiter = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="internal_requisitions_owned"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    target_fill_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "internal_requisitions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Internal Req: {self.title} ({self.status})"


class InternalApplication(models.Model):
    """An internal employee's application to a posted internal role."""

    STATUS_CHOICES = [
        ("applied", "Applied"),
        ("reviewing", "Reviewing"),
        ("shortlisted", "Shortlisted"),
        ("interviewing", "Interviewing"),
        ("offered", "Offered"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_applications")
    requisition = models.ForeignKey(
        InternalRequisition, on_delete=models.CASCADE, related_name="applications"
    )
    applicant = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="internal_applications"
    )
    current_role = models.CharField(max_length=255, blank=True, default="")
    current_department = models.CharField(max_length=150, blank=True, default="")
    cover_note = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")
    current_manager_notified = models.BooleanField(default=False)
    current_manager_approval = models.BooleanField(
        null=True, blank=True, help_text="None=pending, True=approved, False=denied"
    )
    notes = models.TextField(blank=True, default="")
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "internal_applications"
        ordering = ["-applied_at"]
        unique_together = [("requisition", "applicant")]

    def __str__(self):
        return f"{self.applicant_id} → {self.requisition.title} ({self.status})"


class InternalTransferRequest(models.Model):
    """A manager-initiated or employee-initiated lateral/promotion transfer request."""

    TYPE_CHOICES = [
        ("lateral", "Lateral Transfer"),
        ("promotion", "Promotion"),
        ("demotion", "Demotion"),
        ("rotation", "Job Rotation"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="transfer_requests")
    employee = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="transfer_requests"
    )
    transfer_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="lateral")
    from_role = models.CharField(max_length=255)
    from_department = models.CharField(max_length=150, blank=True, default="")
    to_role = models.CharField(max_length=255)
    to_department = models.CharField(max_length=150, blank=True, default="")
    target_job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transfer_requests"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_start_date = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True, default="")
    initiated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="transfers_initiated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "internal_transfer_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transfer: {self.employee_id} {self.from_role} → {self.to_role}"


class ManagerApproval(models.Model):
    """A manager's approval or denial for an internal application or transfer."""

    DECISION_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("denied", "Denied"),
        ("conditionally_approved", "Conditionally Approved"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="manager_approvals")
    internal_application = models.ForeignKey(
        InternalApplication, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="manager_approvals"
    )
    transfer_request = models.ForeignKey(
        InternalTransferRequest, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="manager_approvals"
    )
    manager = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="given_manager_approvals"
    )
    decision = models.CharField(max_length=30, choices=DECISION_CHOICES, default="pending")
    notes = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "manager_approvals"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Manager approval ({self.decision}) by {self.manager_id}"


class InternalVsExternalComparison(models.Model):
    """Analytics snapshot comparing internal vs external candidate pipelines for a job."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="internal_vs_external_comparisons"
    )
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, related_name="internal_vs_external_comparisons"
    )
    internal_applicants = models.IntegerField(default=0)
    external_applicants = models.IntegerField(default=0)
    internal_shortlisted = models.IntegerField(default=0)
    external_shortlisted = models.IntegerField(default=0)
    internal_hired = models.IntegerField(default=0)
    external_hired = models.IntegerField(default=0)
    avg_internal_score = models.FloatField(null=True, blank=True)
    avg_external_score = models.FloatField(null=True, blank=True)
    snapshot_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "internal_vs_external_comparisons"
        ordering = ["-snapshot_date"]

    def __str__(self):
        return f"Int vs Ext comparison — {self.job.title} ({self.snapshot_date})"
