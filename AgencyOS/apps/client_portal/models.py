"""
Client Portal models.
Client login access, portal branding, job-order submission forms,
shortlist review, interview feedback, invoice visibility, timesheet approvals,
worker roster, secure messaging, document sharing, issue escalation.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ClientPortalAccess(models.Model):
    """
    Grants a contact user access to the client portal for a specific client account.
    """

    class AccessLevel(models.TextChoices):
        FULL = "full", "Full Access"
        HIRING_MANAGER = "hiring_manager", "Hiring Manager"
        FINANCE = "finance", "Finance / Invoices Only"
        READ_ONLY = "read_only", "Read Only"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="portal_accesses"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount", on_delete=models.CASCADE, related_name="portal_accesses"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="portal_accesses"
    )
    contact = models.ForeignKey(
        "agency_crm.ClientContact",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="portal_access",
    )
    access_level = models.CharField(
        max_length=20, choices=AccessLevel.choices, default=AccessLevel.HIRING_MANAGER
    )
    is_active = models.BooleanField(default=True)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "portal_access"
        unique_together = [["agency", "client_account", "user"]]

    def __str__(self):
        return f"Portal: {self.user} → {self.client_account} [{self.get_access_level_display()}]"


class PortalJobOrderRequest(models.Model):
    """
    A job order submitted by a client through the portal.
    Gets converted to a JobOrder once reviewed.
    """

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Agency Review"
        INTAKE_CALL_BOOKED = "intake_booked", "Intake Call Booked"
        CONVERTED = "converted", "Converted to Job Order"
        DECLINED = "declined", "Declined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="portal_jo_requests"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount", on_delete=models.CASCADE, related_name="portal_jo_requests"
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="portal_jo_submissions"
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED)
    title = models.CharField(max_length=255)
    staffing_type = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    headcount = models.IntegerField(default=1)
    target_start_date = models.DateField(null=True, blank=True)
    salary_budget = models.CharField(max_length=100, blank=True)
    requirements = models.TextField(blank=True)
    attached_job_order = models.ForeignKey(
        "job_orders.JobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="portal_requests",
    )
    agency_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portal_jo_request"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Portal JO: {self.title} from {self.client_account}"


class PortalShortlistFeedback(models.Model):
    """
    Client feedback on a shortlisted submission via the portal.
    """

    class Decision(models.TextChoices):
        INTERVIEW_YES = "interview_yes", "Yes – Request Interview"
        INTERVIEW_MAYBE = "interview_maybe", "Maybe – Need More Info"
        NO = "no", "No – Not a Fit"
        HOLD = "hold", "Hold for Now"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="portal_feedback"
    )
    submission = models.ForeignKey(
        "submissions.Submission", on_delete=models.CASCADE, related_name="portal_feedbacks"
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="portal_feedback_given"
    )
    decision = models.CharField(max_length=30, choices=Decision.choices)
    rating = models.IntegerField(null=True, blank=True)  # 1-5
    comments = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "portal_shortlist_feedback"
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"Feedback on {self.submission} by {self.reviewed_by}: {self.get_decision_display()}"


class SecureMessage(models.Model):
    """
    Secure message in the client portal between agency team and client contact.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="portal_messages"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount", on_delete=models.CASCADE, related_name="portal_messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_portal_messages"
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    # Reference context
    related_job_order = models.ForeignKey(
        "job_orders.JobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="portal_messages",
    )
    related_submission = models.ForeignKey(
        "submissions.Submission",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="portal_messages",
    )
    attachment_url = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "portal_message"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Message: {self.subject} from {self.sender} to {self.client_account}"


class IssueEscalation(models.Model):
    """
    Issue escalation raised by a client through the portal.
    """

    class IssueType(models.TextChoices):
        CONSULTANT_PERFORMANCE = "consultant_performance", "Consultant Performance"
        BILLING_DISPUTE = "billing_dispute", "Billing Dispute"
        COMPLIANCE = "compliance", "Compliance Issue"
        SERVICE_QUALITY = "service_quality", "Service Quality"
        TIMESHEET_DISPUTE = "timesheet_dispute", "Timesheet Dispute"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="escalations"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount", on_delete=models.CASCADE, related_name="escalations"
    )
    raised_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="raised_escalations"
    )
    assigned_to = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_escalations"
    )
    issue_type = models.CharField(max_length=30, choices=IssueType.choices)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    title = models.CharField(max_length=255)
    description = models.TextField()
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portal_escalation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title} – {self.client_account}"
