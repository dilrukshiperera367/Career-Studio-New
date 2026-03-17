"""
Feature 8 — Hiring Manager Workspace
Models: 15 total
"""
import uuid
from django.conf import settings
from django.db import models


APPROVAL_STATUS = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("needs_revision", "Needs Revision"),
]

PRIORITY = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("critical", "Critical"),
]


# 1. Role Intake Form
class RoleIntakeForm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="role_intakes")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="intake_forms", null=True, blank=True)
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_intake_forms")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recruiter_intake_forms")

    # Role details
    role_title = models.CharField(max_length=255)
    department = models.CharField(max_length=150, blank=True, default="")
    team = models.CharField(max_length=150, blank=True, default="")
    headcount = models.IntegerField(default=1)
    budget_range_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_range_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    target_start_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default="")
    is_remote = models.BooleanField(default=False)
    employment_type = models.CharField(max_length=50, default="full_time")
    priority = models.CharField(max_length=20, choices=PRIORITY, default="medium")

    # Intake content
    ideal_candidate_profile = models.TextField(blank=True, default="")
    must_have_skills = models.JSONField(default=list)
    nice_to_have_skills = models.JSONField(default=list)
    deal_breakers = models.TextField(blank=True, default="")
    team_context = models.TextField(blank=True, default="")
    reporting_structure = models.TextField(blank=True, default="")
    interview_process_notes = models.TextField(blank=True, default="")
    degree_required = models.BooleanField(default=False)
    years_experience_min = models.IntegerField(default=0)

    # Workflow
    status = models.CharField(max_length=30, default="draft")  # draft/submitted/approved/active
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_intakes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_role_intake_forms"
        ordering = ["-created_at"]


# 2. Shortlist Review
class ShortlistReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="shortlist_reviews")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="shortlist_reviews")
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_shortlist_reviews")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recruiter_shortlist_reviews")
    title = models.CharField(max_length=255, default="Shortlist")
    candidates = models.JSONField(default=list)  # list of candidate IDs
    is_locked = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    shared_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_shortlist_reviews"
        ordering = ["-created_at"]


# 3. Candidate Comparison (inside req)
class CandidateComparison(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_comparisons")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="candidate_comparisons")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_comparisons")
    title = models.CharField(max_length=255, default="Comparison")
    candidate_ids = models.JSONField(default=list)
    comparison_criteria = models.JSONField(default=list)  # list of {criterion, weight}
    scores = models.JSONField(default=dict)  # {candidate_id: {criterion: score}}
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_candidate_comparisons"
        ordering = ["-created_at"]


# 4. HM Interview Feedback Inbox item
class HMFeedbackInboxItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_feedback_inbox")
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_feedback_items")
    interview_id = models.UUIDField(null=True, blank=True)  # FK to Interview
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    job_title = models.CharField(max_length=255, blank=True, default="")
    feedback_summary = models.TextField(blank=True, default="")
    recommendation = models.CharField(max_length=30, blank=True, default="")  # hire/no_hire/hold
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hm_feedback_inbox"
        ordering = ["-created_at"]


# 5. HM Approval Task
class HMApprovalTask(models.Model):
    TASK_TYPES = [
        ("shortlist_review", "Shortlist Review"),
        ("offer_approval", "Offer Approval"),
        ("req_approval", "Req Approval"),
        ("intake_review", "Intake Review"),
        ("candidate_advance", "Candidate Advance"),
        ("candidate_reject", "Candidate Reject"),
        ("message_approval", "Message Approval"),
        ("other", "Other"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_approval_tasks")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_hm_tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_hm_tasks")
    task_type = models.CharField(max_length=30, choices=TASK_TYPES, default="other")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    related_object_id = models.UUIDField(null=True, blank=True)
    related_object_type = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default="pending")
    priority = models.CharField(max_length=20, choices=PRIORITY, default="medium")
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_approval_tasks"
        ordering = ["-created_at"]


# 6. Decision Queue Item
class HMDecisionQueueItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_decision_queue")
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_decision_items")
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    job_title = models.CharField(max_length=255, blank=True, default="")
    job_id = models.UUIDField(null=True, blank=True)
    application_id = models.UUIDField(null=True, blank=True)
    decision_type = models.CharField(max_length=30, default="advance")  # advance/reject/hold/offer
    decision = models.CharField(max_length=30, blank=True, default="")
    decision_note = models.TextField(blank=True, default="")
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hm_decision_queue"
        ordering = ["-created_at"]


# 7. Req Health View
class ReqHealthSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="req_health_snapshots")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="health_snapshots")
    snapshotted_at = models.DateTimeField(auto_now_add=True)
    pipeline_total = models.IntegerField(default=0)
    pipeline_by_stage = models.JSONField(default=dict)
    days_open = models.IntegerField(default=0)
    target_days = models.IntegerField(default=45)
    interviews_scheduled = models.IntegerField(default=0)
    offers_extended = models.IntegerField(default=0)
    offers_accepted = models.IntegerField(default=0)
    drop_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    health_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0–100
    health_flags = models.JSONField(default=list)  # list of warning strings

    class Meta:
        db_table = "hm_req_health_snapshots"
        ordering = ["-snapshotted_at"]


# 8. Time-to-Fill Risk
class TimeToFillRisk(models.Model):
    RISK_LEVELS = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="ttf_risks")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="ttf_risks")
    assessed_at = models.DateTimeField(auto_now_add=True)
    days_open = models.IntegerField(default=0)
    target_fill_days = models.IntegerField(default=45)
    predicted_fill_days = models.IntegerField(null=True, blank=True)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default="medium")
    risk_factors = models.JSONField(default=list)
    recommended_actions = models.JSONField(default=list)

    class Meta:
        db_table = "hm_ttf_risks"
        ordering = ["-assessed_at"]


# 9. Candidate Messaging Approval
class CandidateMessageApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="message_approvals")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_message_approvals")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_message_approvals")
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    message_subject = models.CharField(max_length=255, blank=True, default="")
    message_body = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default="pending")
    reviewer_note = models.TextField(blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hm_message_approvals"
        ordering = ["-created_at"]


# 10. HM SLA Reminder
class HMSLAReminder(models.Model):
    SLA_TYPES = [
        ("shortlist_review", "Shortlist Review"),
        ("feedback_submission", "Feedback Submission"),
        ("offer_approval", "Offer Approval"),
        ("req_approval", "Req Approval"),
        ("decision", "Decision"),
        ("intake_completion", "Intake Completion"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_sla_reminders")
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_sla_reminders")
    sla_type = models.CharField(max_length=30, choices=SLA_TYPES, default="decision")
    related_object_id = models.UUIDField(null=True, blank=True)
    due_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hm_sla_reminders"
        ordering = ["-created_at"]


# 11. Calibration View (HM-facing calibration summary)
class HMCalibrationView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_calibration_views")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="hm_calibration_views")
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_calibration_entries")
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    application_id = models.UUIDField(null=True, blank=True)
    interviewer_scores = models.JSONField(default=dict)  # {interviewer_name: score}
    consensus_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hm_recommendation = models.CharField(max_length=30, blank=True, default="")
    hm_notes = models.TextField(blank=True, default="")
    calibration_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_calibration_views"
        ordering = ["-created_at"]


# 12. Offer Approval (HM-facing)
class HMOfferApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_offer_approvals")
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_offer_approvals")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recruiter_hm_offer_approvals")
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    job_title = models.CharField(max_length=255, blank=True, default="")
    offer_id = models.UUIDField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_comp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    offer_details = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default="pending")
    decision_note = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_offer_approvals"
        ordering = ["-created_at"]


# 13. Recruiter-Manager Collaboration Note
class RecruiterManagerNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="recruiter_manager_notes")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="recruiter_manager_notes", null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="authored_collab_notes")
    tagged_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tagged_collab_notes")
    note_type = models.CharField(max_length=30, default="general")  # general/strategy/concern/update
    body = models.TextField()
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_recruiter_manager_notes"
        ordering = ["-created_at"]


# 14. Manager Training Prompt
class ManagerTrainingPrompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="manager_training_prompts")
    trigger_event = models.CharField(max_length=50, default="shortlist_review")  # event that surfaces this prompt
    title = models.CharField(max_length=255)
    body = models.TextField()
    resource_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hm_training_prompts"
        ordering = ["trigger_event", "title"]


# 15. HM Dashboard Stat (cached per job/manager)
class HMDashboardStat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_dashboard_stats")
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="hm_dashboard_stats")
    computed_at = models.DateTimeField(auto_now=True)
    open_reqs = models.IntegerField(default=0)
    pending_approvals = models.IntegerField(default=0)
    pending_feedback = models.IntegerField(default=0)
    pending_decisions = models.IntegerField(default=0)
    overdue_slas = models.IntegerField(default=0)
    active_offers = models.IntegerField(default=0)
    avg_ttf_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    reqs_at_risk = models.IntegerField(default=0)

    class Meta:
        db_table = "hm_dashboard_stats"
        ordering = ["-computed_at"]
