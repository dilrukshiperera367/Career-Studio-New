"""
Feature 10 — Internal Recruiting Bridge
Models: 14 total
"""
import uuid
from django.conf import settings
from django.db import models


# 1. Internal Requisition
class InternalRequisition(models.Model):
    VISIBILITY = [("internal_only", "Internal Only"), ("internal_first", "Internal First"), ("public", "Public")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_requisitions")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="internal_requisitions", null=True, blank=True)
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=150, blank=True, default="")
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default="internal_only")
    internal_posting_opens_at = models.DateTimeField(null=True, blank=True)
    public_posting_opens_at = models.DateTimeField(null=True, blank=True)
    is_gig = models.BooleanField(default=False)  # internal gig/project role
    gig_duration_weeks = models.IntegerField(default=0)
    requires_manager_approval = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")
    skills_required = models.JSONField(default=list)
    status = models.CharField(max_length=30, default="draft")  # draft/open/closed/filled
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_internal_reqs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ib_internal_requisitions"
        ordering = ["-created_at"]


# 2. Internal Posting Window
class InternalPostingWindow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_posting_windows")
    internal_req = models.ForeignKey(InternalRequisition, on_delete=models.CASCADE, related_name="posting_windows")
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    notified_employees = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    notification_channels = models.JSONField(default=list)  # email/slack/intranet
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ib_internal_posting_windows"
        ordering = ["-opens_at"]


# 3. Internal Candidate (employee → applicant conversion)
class InternalCandidate(models.Model):
    SOURCE_TYPES = [
        ("internal_apply", "Internal Apply"),
        ("manager_referred", "Manager Referred"),
        ("talent_marketplace", "Talent Marketplace"),
        ("internal_referral", "Internal Referral"),
        ("rehire", "Rehire"),
        ("alumni", "Alumni Fast-Track"),
    ]
    CONFIDENTIALITY = [("standard", "Standard"), ("confidential", "Confidential"), ("highly_confidential", "Highly Confidential")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_candidates")
    employee_id = models.CharField(max_length=100, blank=True, default="")  # HRM employee ID
    employee_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="internal_candidacies")
    candidate_id = models.UUIDField(null=True, blank=True)  # linked Candidate model ID
    application_id = models.UUIDField(null=True, blank=True)
    internal_req = models.ForeignKey(InternalRequisition, on_delete=models.CASCADE, related_name="internal_candidates", null=True, blank=True)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES, default="internal_apply")
    current_role = models.CharField(max_length=255, blank=True, default="")
    current_department = models.CharField(max_length=150, blank=True, default="")
    current_manager_id = models.CharField(max_length=100, blank=True, default="")
    years_at_company = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    confidentiality_level = models.CharField(max_length=25, choices=CONFIDENTIALITY, default="standard")
    manager_notified = models.BooleanField(default=False)
    manager_approved = models.BooleanField(default=False)
    manager_approval_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, default="applied")  # applied/screening/interviewing/offered/accepted/declined/withdrawn
    is_rehire = models.BooleanField(default=False)
    is_alumni = models.BooleanField(default=False)
    fast_tracked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ib_internal_candidates"
        ordering = ["-created_at"]


# 4. Internal Transfer Workflow
class InternalTransferWorkflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_transfer_workflows")
    internal_candidate = models.ForeignKey(InternalCandidate, on_delete=models.CASCADE, related_name="transfer_workflows")
    from_department = models.CharField(max_length=150, blank=True, default="")
    from_role = models.CharField(max_length=255, blank=True, default="")
    to_department = models.CharField(max_length=150, blank=True, default="")
    to_role = models.CharField(max_length=255, blank=True, default="")
    from_manager_approval = models.CharField(max_length=20, default="pending")  # pending/approved/rejected
    from_manager_approved_at = models.DateTimeField(null=True, blank=True)
    to_manager_approval = models.CharField(max_length=20, default="pending")
    to_manager_approved_at = models.DateTimeField(null=True, blank=True)
    hr_approval = models.CharField(max_length=20, default="pending")
    hr_approved_at = models.DateTimeField(null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    transition_plan = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, default="initiated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ib_internal_transfer_workflows"
        ordering = ["-created_at"]


# 5. Employee Skill Profile Bridge
class EmployeeSkillProfileBridge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="employee_skill_bridges")
    employee_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="skill_bridge_profiles")
    employee_id = models.CharField(max_length=100, blank=True, default="")
    skills = models.JSONField(default=list)  # [{skill, level, verified}]
    certifications = models.JSONField(default=list)
    interests = models.JSONField(default=list)
    career_goals = models.TextField(blank=True, default="")
    open_to_gig = models.BooleanField(default=False)
    open_to_transfer = models.BooleanField(default=False)
    last_synced_from_hrm_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ib_employee_skill_bridges"
        ordering = ["-updated_at"]


# 6. Internal Referral
class InternalReferral(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_referrals")
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="made_internal_referrals")
    internal_req = models.ForeignKey(InternalRequisition, on_delete=models.CASCADE, related_name="internal_referrals", null=True, blank=True)
    referred_employee_id = models.CharField(max_length=100, blank=True, default="")
    referred_employee_name = models.CharField(max_length=255, blank=True, default="")
    referral_note = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, default="submitted")  # submitted/accepted/rejected/hired
    bonus_eligible = models.BooleanField(default=False)
    bonus_paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ib_internal_referrals"
        ordering = ["-created_at"]


# 7. Rehire / Alumni Fast-Track Record
class RehireAlumniRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="rehire_alumni_records")
    candidate_id = models.UUIDField(null=True, blank=True)
    employee_id = models.CharField(max_length=100, blank=True, default="")
    name = models.CharField(max_length=255)
    previous_department = models.CharField(max_length=150, blank=True, default="")
    previous_role = models.CharField(max_length=255, blank=True, default="")
    previous_tenure_months = models.IntegerField(default=0)
    separation_date = models.DateField(null=True, blank=True)
    separation_type = models.CharField(max_length=30, default="voluntary")  # voluntary/involuntary/layoff/contract_end
    rehire_eligible = models.BooleanField(default=True)
    rehire_notes = models.TextField(blank=True, default="")
    fast_track_approved = models.BooleanField(default=False)
    applied_to_req = models.ForeignKey(InternalRequisition, on_delete=models.SET_NULL, null=True, blank=True, related_name="rehire_alumni")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ib_rehire_alumni_records"
        ordering = ["-created_at"]


# 8. Internal vs External Pipeline Comparison
class PipelineComparison(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="pipeline_comparisons")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="pipeline_comparisons")
    snapshotted_at = models.DateTimeField(auto_now_add=True)
    internal_total = models.IntegerField(default=0)
    external_total = models.IntegerField(default=0)
    internal_advance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    external_advance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    internal_offer_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    external_offer_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    internal_hire_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    external_hire_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    internal_avg_ttf_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    external_avg_ttf_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    class Meta:
        db_table = "ib_pipeline_comparisons"
        ordering = ["-snapshotted_at"]


# 9. Internal Candidate Compare View
class InternalCandidateCompare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_candidate_compares")
    internal_req = models.ForeignKey(InternalRequisition, on_delete=models.CASCADE, related_name="candidate_compares")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="internal_compares")
    candidate_ids = models.JSONField(default=list)  # internal candidate IDs
    comparison_dimensions = models.JSONField(default=list)  # skills, tenure, performance, etc.
    scores = models.JSONField(default=dict)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ib_internal_candidate_compares"
        ordering = ["-created_at"]


# 10. Manager Approval for Internal Applicant
class ManagerInternalApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="manager_internal_approvals")
    internal_candidate = models.ForeignKey(InternalCandidate, on_delete=models.CASCADE, related_name="manager_approvals")
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="given_manager_approvals")
    status = models.CharField(max_length=20, default="pending")  # pending/approved/rejected/conditional
    decision_note = models.TextField(blank=True, default="")
    conditions = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ib_manager_internal_approvals"
        ordering = ["-created_at"]


# 11. Confidentiality Control
class InternalCandidacyConfidentialityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="confidentiality_logs")
    internal_candidate = models.ForeignKey(InternalCandidate, on_delete=models.CASCADE, related_name="confidentiality_logs")
    action = models.CharField(max_length=50)  # viewed/updated/shared/redacted
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="confidentiality_actions")
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ib_confidentiality_logs"
        ordering = ["-created_at"]


# 12. Talent Marketplace Usage Stat (SHRM data point: 25%→35%)
class TalentMarketplaceUsageStat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="talent_marketplace_stats")
    period_start = models.DateField()
    period_end = models.DateField()
    total_employees = models.IntegerField(default=0)
    employees_browsed = models.IntegerField(default=0)
    employees_applied = models.IntegerField(default=0)
    employees_hired_internally = models.IntegerField(default=0)
    gig_completions = models.IntegerField(default=0)
    internal_mobility_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ib_talent_marketplace_stats"
        ordering = ["-period_start"]


# 13. Internal Job Alert / Notification
class InternalJobAlert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_job_alerts")
    employee_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="internal_job_alerts")
    internal_req = models.ForeignKey(InternalRequisition, on_delete=models.CASCADE, related_name="job_alerts")
    channel = models.CharField(max_length=20, default="email")  # email/slack/in_app
    sent_at = models.DateTimeField(null=True, blank=True)
    opened = models.BooleanField(default=False)
    clicked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ib_internal_job_alerts"
        ordering = ["-created_at"]


# 14. Internal Gig Assignment
class InternalGigAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="internal_gig_assignments")
    internal_req = models.ForeignKey(InternalRequisition, on_delete=models.CASCADE, related_name="gig_assignments")
    internal_candidate = models.ForeignKey(InternalCandidate, on_delete=models.CASCADE, related_name="gig_assignments")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    hours_per_week = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    status = models.CharField(max_length=20, default="active")  # active/completed/cancelled
    outcome_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ib_internal_gig_assignments"
        ordering = ["-created_at"]
