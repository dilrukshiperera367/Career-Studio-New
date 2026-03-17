"""
Manager Hub — models for the manager dashboard, team management, approvals, and coaching tools.
"""

import uuid
from django.db import models
from django.conf import settings


class ManagerDashboardConfig(models.Model):
    """Per-manager dashboard configuration and preferences."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='manager_dashboard_configs')
    manager = models.OneToOneField('core_hr.Employee', on_delete=models.CASCADE, related_name='dashboard_config')
    pinned_widgets = models.JSONField(default=list, help_text='["team_attendance","pending_approvals","team_goals"]')
    layout = models.JSONField(default=dict, help_text='Widget grid layout positions')
    default_team_view = models.CharField(
        max_length=20, default='list',
        choices=[('list', 'List'), ('grid', 'Grid'), ('org_chart', 'Org Chart')]
    )
    show_indirect_reports = models.BooleanField(default=False)
    notification_prefs = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'manager_dashboard_configs'

    def __str__(self):
        return f"Dashboard config for {self.manager}"


class TeamAlert(models.Model):
    """Actionable alert surfaced on the manager dashboard."""
    ALERT_TYPES = [
        ('probation_due', 'Probation Review Due'),
        ('contract_expiry', 'Contract Expiry Approaching'),
        ('leave_overdue', 'Leave Request Pending'),
        ('attendance_anomaly', 'Attendance Anomaly'),
        ('goal_at_risk', 'Goal At Risk'),
        ('certification_expiry', 'Certification Expiry'),
        ('performance_review_due', 'Performance Review Due'),
        ('high_attrition_risk', 'High Attrition Risk'),
        ('birthday', 'Team Birthday'),
        ('work_anniversary', 'Work Anniversary'),
    ]
    SEVERITY_CHOICES = [('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='team_alerts')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='team_alerts')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='alerts_about_me')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    title = models.CharField(max_length=300)
    message = models.TextField(blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'team_alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.alert_type}: {self.title}"


class OneOnOne(models.Model):
    """Scheduled 1:1 meeting between manager and direct report."""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('rescheduled', 'Rescheduled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='one_on_ones')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='one_on_ones_as_manager')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='one_on_ones_as_employee')
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    location = models.CharField(max_length=200, blank=True, help_text="Room, Zoom link, etc.")
    agenda = models.JSONField(default=list, help_text='[{"topic":"Career goals","notes":"...","added_by":"manager"}]')
    notes = models.TextField(blank=True, help_text='Shared meeting notes')
    manager_notes = models.TextField(blank=True, help_text='Private manager notes')
    action_items = models.JSONField(default=list,
        help_text='[{"item":"Share development plan","owner":"employee","due":"2024-03-15","done":false}]')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    recurrence = models.CharField(
        max_length=20, blank=True,
        choices=[('none', 'None'), ('weekly', 'Weekly'), ('biweekly', 'Biweekly'), ('monthly', 'Monthly')]
    )
    recurrence_parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='recurrences')
    talk_about = models.JSONField(default=list, help_text='Shared talking points added by employee')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'one_on_ones'
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"1:1 {self.manager} / {self.employee} @ {self.scheduled_at:%Y-%m-%d}"


class CoachingNote(models.Model):
    """Private coaching notes a manager records about a direct report."""
    NOTE_TYPES = [
        ('observation', 'Observation'), ('coaching', 'Coaching Session'),
        ('commendation', 'Commendation'), ('concern', 'Concern'),
        ('development', 'Development Note'), ('pip_note', 'PIP Note'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='coaching_notes')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='coaching_notes_given')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='coaching_notes_received')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='observation')
    title = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    tags = models.JSONField(default=list)
    is_shared_with_hr = models.BooleanField(default=False)
    related_one_on_one = models.ForeignKey(OneOnOne, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='coaching_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'coaching_notes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.note_type}: {self.employee} by {self.manager}"


class TeamPerformanceSummary(models.Model):
    """Cached team performance summary snapshot for manager dashboard."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='team_performance_summaries')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='team_performance_summaries')
    period_year = models.IntegerField()
    period_month = models.IntegerField(null=True, blank=True, help_text='Null = annual summary')
    headcount = models.IntegerField(default=0)
    avg_performance_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    avg_attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_goal_progress = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pending_approvals = models.IntegerField(default=0)
    open_leave_requests = models.IntegerField(default=0)
    attrition_risk_high = models.IntegerField(default=0)
    attrition_risk_medium = models.IntegerField(default=0)
    engagement_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    top_performers = models.JSONField(default=list)
    at_risk_employees = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'team_performance_summaries'
        unique_together = ['manager', 'period_year', 'period_month']
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f"Team summary for {self.manager} — {self.period_year}"


class DelegationRule(models.Model):
    """Manager delegation — delegate approval authority during absence."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='delegation_rules')
    delegator = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='delegations_given')
    delegate = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='delegations_received')
    start_date = models.DateField()
    end_date = models.DateField()
    scope = models.JSONField(default=list,
        help_text='["leave_approval","expense_approval","timesheet_approval"]')
    reason = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'delegation_rules'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.delegator} → {self.delegate} ({self.start_date} to {self.end_date})"


# ---------------------------------------------------------------------------
# Feature 3 additions
# ---------------------------------------------------------------------------

class TeamRosterView(models.Model):
    """Cached team roster snapshot for manager's team directory."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='team_roster_views')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='team_roster_views')
    include_indirect = models.BooleanField(default=False)
    headcount = models.IntegerField(default=0)
    roster_data = models.JSONField(default=list,
        help_text='[{"employee_id":...,"name":...,"role":...,"status":...,"shift":...}]')
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'team_roster_views'
        unique_together = ['manager', 'include_indirect']

    def __str__(self):
        return f"Roster for {self.manager} (indirect={self.include_indirect})"


class TeamAttendanceSnapshot(models.Model):
    """Daily/weekly attendance and leave snapshot for a manager's team."""
    PERIOD_TYPES = [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='team_attendance_snapshots')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='team_attendance_snapshots')
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES, default='daily')
    period_start = models.DateField()
    period_end = models.DateField()
    total_headcount = models.IntegerField(default=0)
    present_count = models.IntegerField(default=0)
    absent_count = models.IntegerField(default=0)
    on_leave_count = models.IntegerField(default=0)
    late_count = models.IntegerField(default=0)
    wfh_count = models.IntegerField(default=0)
    overtime_hours_total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    pending_leave_approvals = models.IntegerField(default=0)
    pending_ot_approvals = models.IntegerField(default=0)
    attendance_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    detail = models.JSONField(default=list,
        help_text='Per-employee breakdown [{"employee_id":...,"status":...,"hours":...}]')
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'team_attendance_snapshots'
        ordering = ['-period_start']

    def __str__(self):
        return f"Attendance {self.period_type} {self.period_start} — {self.manager}"


class ApprovalItem(models.Model):
    """Unified approvals queue item for a manager (leave, OT, expense, etc.)."""
    ITEM_TYPES = [
        ('leave', 'Leave Request'),
        ('overtime', 'Overtime'),
        ('expense', 'Expense'),
        ('shift_swap', 'Shift Swap'),
        ('wfh', 'WFH Request'),
        ('comp_change', 'Compensation Change'),
        ('promotion', 'Promotion'),
        ('offboarding', 'Offboarding'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('delegated', 'Delegated'), ('escalated', 'Escalated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='approval_items')
    approver = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='approval_items')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='approval_requests')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    reference_id = models.UUIDField(help_text='PK of the source object (LeaveRequest, OvertimeRecord, etc.)')
    reference_app = models.CharField(max_length=50, help_text='e.g. leave_attendance, payroll')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, default='medium',
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    delegated_to = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='delegated_approvals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'approval_items'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'approver', 'status'], name='idx_approval_approver_status'),
        ]

    def __str__(self):
        return f"{self.item_type}: {self.title} ({self.status})"


class OnboardingOffboardingTracker(models.Model):
    """Manager control-tower view of active onboarding / offboarding activities."""
    TRACKER_TYPES = [('onboarding', 'Onboarding'), ('offboarding', 'Offboarding')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='ob_ob_trackers')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='ob_ob_trackers')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='ob_ob_tracked')
    tracker_type = models.CharField(max_length=15, choices=TRACKER_TYPES)
    target_date = models.DateField(help_text='Join date (onboarding) or last working day (offboarding)')
    overall_completion_pct = models.IntegerField(default=0)
    tasks_total = models.IntegerField(default=0)
    tasks_completed = models.IntegerField(default=0)
    tasks_overdue = models.IntegerField(default=0)
    blockers = models.JSONField(default=list, help_text='List of blocking task descriptions')
    manager_actions_needed = models.JSONField(default=list)
    status = models.CharField(max_length=20, default='active',
        choices=[('active', 'Active'), ('completed', 'Completed'), ('at_risk', 'At Risk'), ('stalled', 'Stalled')])
    last_refreshed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'ob_ob_trackers'
        unique_together = ['tenant', 'employee', 'tracker_type']
        ordering = ['target_date']

    def __str__(self):
        return f"{self.tracker_type}: {self.employee} (manager={self.manager})"


class SkillGapSummary(models.Model):
    """Skill gap analysis snapshot for a manager's team."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='skill_gap_summaries')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='skill_gap_summaries')
    analysis_date = models.DateField()
    team_size = models.IntegerField(default=0)
    critical_gaps = models.JSONField(default=list,
        help_text='[{"skill":"Python","required_level":4,"avg_team_level":2,"gap_employees":[...]}]')
    skill_distribution = models.JSONField(default=dict)
    learning_recommendations = models.JSONField(default=list)
    coverage_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        help_text='% of required skills adequately covered by team')
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'skill_gap_summaries'
        ordering = ['-analysis_date']

    def __str__(self):
        return f"Skill Gap for {self.manager} — {self.analysis_date}"


class FlightRiskAlert(models.Model):
    """Flight-risk and engagement alert for a specific employee on a manager's team."""
    RISK_LEVELS = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='flight_risk_alerts')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='flight_risk_alerts')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='flight_risk_flagged')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='medium')
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0,
        help_text='0-100 composite flight risk score')
    engagement_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    risk_factors = models.JSONField(default=list,
        help_text='["low eNPS","no promotion in 3y","peer left","market salary gap"]')
    recommended_actions = models.JSONField(default=list)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'flight_risk_alerts'
        ordering = ['-risk_score']

    def __str__(self):
        return f"Flight risk {self.risk_level}: {self.employee}"


class SuccessionPlanEntry(models.Model):
    """Succession planning — readiness of a potential successor for a role."""
    READINESS_CHOICES = [
        ('ready_now', 'Ready Now'),
        ('ready_1y', 'Ready in 1 Year'),
        ('ready_2y', 'Ready in 2 Years'),
        ('development_needed', 'Development Needed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='succession_plan_entries')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='succession_plans_owned')
    target_role_employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE,
                                              related_name='succession_role_for',
                                              help_text='Employee whose role is being succession-planned')
    successor = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='succession_nominee')
    readiness = models.CharField(max_length=20, choices=READINESS_CHOICES, default='ready_2y')
    bench_rank = models.IntegerField(default=1, help_text='1 = primary successor, 2 = secondary, etc.')
    development_actions = models.JSONField(default=list)
    strengths = models.JSONField(default=list)
    gaps = models.JSONField(default=list)
    retention_risk = models.CharField(max_length=10, default='low',
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    notes = models.TextField(blank=True)
    reviewed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'succession_plan_entries'
        unique_together = ['tenant', 'target_role_employee', 'successor']
        ordering = ['bench_rank']

    def __str__(self):
        return f"{self.successor} → {self.target_role_employee} ({self.readiness})"


class CompPlanningWorkspace(models.Model):
    """Manager compensation planning workspace within a merit cycle."""
    STATUS_CHOICES = [
        ('open', 'Open'), ('submitted', 'Submitted'), ('locked', 'Locked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='comp_planning_workspaces')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='comp_planning_workspaces')
    cycle_id = models.UUIDField(help_text='UUID of MeritCycle in total_rewards')
    cycle_name = models.CharField(max_length=200, blank=True)
    total_budget = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    allocated_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    remaining_budget = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    team_size_eligible = models.IntegerField(default=0)
    recommendations = models.JSONField(default=list,
        help_text='[{"employee_id":...,"current":...,"recommended":...,"merit_pct":...,"bonus":...,"notes":"..."}]')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'comp_planning_workspaces'
        unique_together = ['tenant', 'manager', 'cycle_id']

    def __str__(self):
        return f"Comp workspace: {self.manager} — {self.cycle_name}"


class RecognitionAction(models.Model):
    """Manager recognition or coaching action directed at a team member."""
    ACTION_TYPES = [
        ('shoutout', 'Public Shoutout'),
        ('peer_nomination', 'Peer Nomination'),
        ('spot_award', 'Spot Award'),
        ('coaching_session', 'Coaching Session'),
        ('pip_initiation', 'PIP Initiation'),
        ('development_plan', 'Development Plan'),
        ('kudos', 'Kudos'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='recognition_actions')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='recognition_actions_given')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='recognition_actions_received')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    title = models.CharField(max_length=300)
    message = models.TextField(blank=True)
    award_value = models.DecimalField(max_digits=10, decimal_places=2, default=0,
        help_text='Monetary value of spot award if applicable')
    is_public = models.BooleanField(default=True)
    tags = models.JSONField(default=list, help_text='Core value tags e.g. ["ownership","innovation"]')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'recognition_actions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action_type}: {self.manager} → {self.employee}"


class TrainingCompletionView(models.Model):
    """Cached mandatory training completion status per employee on a manager's team."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='training_completion_views')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='training_completion_views')
    period_label = models.CharField(max_length=30, help_text='e.g. Q1-2025 or Annual-2025')
    team_size = models.IntegerField(default=0)
    fully_compliant_count = models.IntegerField(default=0)
    partially_compliant_count = models.IntegerField(default=0)
    non_compliant_count = models.IntegerField(default=0)
    overdue_count = models.IntegerField(default=0)
    compliance_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    detail = models.JSONField(default=list,
        help_text='[{"employee_id":...,"courses_required":3,"completed":2,"overdue":["GDPR Training"]}]')
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'training_completion_views'
        unique_together = ['tenant', 'manager', 'period_label']

    def __str__(self):
        return f"Training compliance {self.period_label} — {self.manager}"


class WorkforceCostSnapshot(models.Model):
    """Monthly workforce cost snapshot for a manager's team."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='workforce_cost_snapshots')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='workforce_cost_snapshots')
    period_year = models.IntegerField()
    period_month = models.IntegerField()
    headcount = models.IntegerField(default=0)
    total_gross_payroll = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_employer_cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_overtime_cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_benefits_cost = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    avg_cost_per_employee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    budget_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    budget_variance_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    breakdown = models.JSONField(default=dict)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'workforce_cost_snapshots'
        unique_together = ['tenant', 'manager', 'period_year', 'period_month']
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f"Cost {self.period_year}-{self.period_month:02d} — {self.manager}"


class ScheduleCoverageAlert(models.Model):
    """Alert for shift coverage gaps or fatigue risks on a manager's schedule."""
    ALERT_TYPES = [
        ('coverage_gap', 'Coverage Gap'),
        ('understaffed', 'Understaffed Shift'),
        ('shift_conflict', 'Shift Conflict'),
        ('fatigue_risk', 'Fatigue / Rest Period Risk'),
        ('overtime_threshold', 'Overtime Threshold Breached'),
        ('no_show', 'No-Show Risk'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='schedule_coverage_alerts')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='schedule_coverage_alerts')
    alert_type = models.CharField(max_length=25, choices=ALERT_TYPES)
    affected_date = models.DateField()
    affected_shift = models.CharField(max_length=100, blank=True)
    severity = models.CharField(max_length=10, default='warning',
        choices=[('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')])
    affected_employees = models.JSONField(default=list)
    description = models.TextField()
    suggested_action = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'schedule_coverage_alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.alert_type} on {self.affected_date} ({self.severity})"


class ActionRecommendation(models.Model):
    """AI/rules-driven action recommendation for people managers."""
    RECOMMENDATION_CATEGORIES = [
        ('retention', 'Retention Action'),
        ('recognition', 'Recognition Opportunity'),
        ('development', 'Development Opportunity'),
        ('compliance', 'Compliance Action'),
        ('wellbeing', 'Wellbeing Check-in'),
        ('performance', 'Performance Conversation'),
        ('scheduling', 'Scheduling Optimization'),
        ('compensation', 'Compensation Review'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='action_recommendations')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='action_recommendations')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='action_recs_about_me')
    category = models.CharField(max_length=20, choices=RECOMMENDATION_CATEGORIES)
    priority_score = models.IntegerField(default=50, help_text='0-100; higher = more urgent')
    title = models.CharField(max_length=300)
    description = models.TextField()
    suggested_actions = models.JSONField(default=list)
    evidence = models.JSONField(default=dict, help_text='Supporting signals driving the recommendation')
    is_dismissed = models.BooleanField(default=False)
    is_actioned = models.BooleanField(default=False)
    actioned_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'manager_hub'
        db_table = 'action_recommendations'
        ordering = ['-priority_score', '-generated_at']

    def __str__(self):
        return f"{self.category}: {self.title} (score={self.priority_score})"
