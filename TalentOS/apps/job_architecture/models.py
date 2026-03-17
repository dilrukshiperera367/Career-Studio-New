"""Job Architecture app — Job families, levels, competencies, headcount planning, salary bands."""

import uuid
from django.db import models


class JobFamily(models.Model):
    """A grouping of related job roles (e.g. Engineering, Sales, Finance)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_families")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_families"
        ordering = ["name"]
        unique_together = [("tenant", "code")]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class JobLevel(models.Model):
    """Career level within a job family (e.g. IC1–IC7, M1–M5)."""

    LEVEL_TYPE_CHOICES = [
        ("ic", "Individual Contributor"),
        ("manager", "Manager"),
        ("director", "Director"),
        ("vp", "VP / Executive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_levels")
    job_family = models.ForeignKey(JobFamily, on_delete=models.CASCADE, related_name="levels")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True, default="")
    level_type = models.CharField(max_length=20, choices=LEVEL_TYPE_CHOICES, default="ic")
    numeric_level = models.IntegerField(default=1, help_text="Numeric ordering within the family")
    scope = models.TextField(blank=True, default="", help_text="What a person at this level owns/decides")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_levels"
        ordering = ["job_family", "numeric_level"]
        unique_together = [("tenant", "job_family", "numeric_level")]

    def __str__(self):
        return f"{self.job_family.name} / {self.name}"


class CompetencyFramework(models.Model):
    """A named set of competencies (e.g. 'Leadership Framework 2025')."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="competency_frameworks")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "competency_frameworks"

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class Competency(models.Model):
    """An individual competency (skill/behaviour) within a framework."""

    PROFICIENCY_CHOICES = [
        ("awareness", "Awareness"),
        ("working", "Working"),
        ("practitioner", "Practitioner"),
        ("expert", "Expert"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="competencies")
    framework = models.ForeignKey(CompetencyFramework, on_delete=models.CASCADE, related_name="competencies")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=100, blank=True, default="", help_text="e.g. Technical, Leadership, Soft")
    required_for_levels = models.JSONField(default=list, blank=True,
        help_text="List of JobLevel UUIDs where this competency is required")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "competencies"
        ordering = ["framework", "name"]

    def __str__(self):
        return f"{self.name} ({self.framework.name})"


class HeadcountPlan(models.Model):
    """Annual / quarterly headcount plan for a department."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="headcount_plans")
    name = models.CharField(max_length=255)
    fiscal_year = models.IntegerField()
    quarter = models.IntegerField(null=True, blank=True, help_text="1–4; null = full year")
    department = models.CharField(max_length=150, blank=True, default="")
    owner = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="owned_headcount_plans")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    total_headcount = models.IntegerField(default=0)
    approved_headcount = models.IntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "headcount_plans"
        ordering = ["-fiscal_year", "department"]

    def __str__(self):
        return f"{self.name} FY{self.fiscal_year}"


class HeadcountRequisition(models.Model):
    """A single open seat in a headcount plan."""

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("filled", "Filled"),
        ("cancelled", "Cancelled"),
        ("deferred", "Deferred"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="headcount_requisitions")
    plan = models.ForeignKey(HeadcountPlan, on_delete=models.CASCADE, related_name="requisitions")
    job_family = models.ForeignKey(JobFamily, on_delete=models.SET_NULL, null=True, blank=True, related_name="requisitions")
    job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name="requisitions")
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=150, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    target_start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    linked_job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="headcount_requisitions"
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "headcount_requisitions"
        ordering = ["plan", "title"]

    def __str__(self):
        return f"{self.title} — {self.plan.name}"


class SalaryBand(models.Model):
    """Pay range for a job family + level combination."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="salary_bands")
    job_family = models.ForeignKey(JobFamily, on_delete=models.CASCADE, related_name="salary_bands")
    job_level = models.ForeignKey(JobLevel, on_delete=models.CASCADE, related_name="salary_bands")
    currency = models.CharField(max_length=3, default="USD")
    pay_range_min = models.DecimalField(max_digits=14, decimal_places=2)
    pay_range_mid = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    pay_range_max = models.DecimalField(max_digits=14, decimal_places=2)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    geo_zone = models.CharField(max_length=100, blank=True, default="", help_text="e.g. SF Bay Area, Remote-US, UK")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "salary_bands"
        ordering = ["job_family", "job_level", "geo_zone"]

    def __str__(self):
        return f"{self.job_family.name} / {self.job_level.name} — {self.geo_zone or 'Global'}"


class JobDescriptionVersion(models.Model):
    """Versioned copy of a job description with quality/language scoring."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="jd_versions")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="jd_versions")
    version_number = models.IntegerField(default=1)
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField(blank=True, default="")
    inclusive_language_score = models.FloatField(null=True, blank=True, help_text="0–100 inclusive language score")
    jd_quality_score = models.FloatField(null=True, blank=True, help_text="0–100 overall quality score")
    inclusive_language_flags = models.JSONField(default=list, blank=True,
        help_text="[{'term': 'ninja', 'suggestion': 'engineer', 'severity': 'medium'}]")
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="jd_versions")
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_description_versions"
        ordering = ["job", "-version_number"]

    def __str__(self):
        return f"{self.job.title} v{self.version_number}"


class ApprovalChain(models.Model):
    """Reusable approval chain template for offers, headcount, etc."""

    CHAIN_TYPE_CHOICES = [
        ("offer", "Offer Approval"),
        ("headcount", "Headcount Approval"),
        ("job_publish", "Job Publish Approval"),
        ("general", "General"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="approval_chains")
    name = models.CharField(max_length=255)
    chain_type = models.CharField(max_length=20, choices=CHAIN_TYPE_CHOICES, default="general")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "approval_chains"

    def __str__(self):
        return f"{self.name} ({self.get_chain_type_display()})"


class ApprovalStep(models.Model):
    """A single step within an approval chain."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="approval_steps")
    chain = models.ForeignKey(ApprovalChain, on_delete=models.CASCADE, related_name="steps")
    order = models.IntegerField(default=1)
    approver = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_steps"
    )
    approver_role = models.CharField(max_length=100, blank=True, default="",
        help_text="Role-based fallback if approver is unset")
    is_required = models.BooleanField(default=True)
    timeout_hours = models.IntegerField(default=48, help_text="Auto-escalate after this many hours")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approval_steps"
        ordering = ["chain", "order"]

    def __str__(self):
        return f"Step {self.order} — {self.chain.name}"


# ── Hiring Team Templates ──────────────────────────────────────────────────────

class HiringTeamTemplate(models.Model):
    """
    Reusable hiring team assignment template.
    Defines default recruiter, coordinator, and interviewers for a role type.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hiring_team_templates")
    name = models.CharField(max_length=255, help_text="e.g. 'Engineering Full-Cycle Team'")
    job_family = models.ForeignKey(
        JobFamily, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hiring_team_templates",
    )
    recruiter = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="htt_recruiter",
    )
    coordinator = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="htt_coordinator",
    )
    interviewers = models.JSONField(
        default=list, blank=True,
        help_text='[{"user_id": "...", "round": 1, "focus": "Technical"}]'
    )
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hiring_team_templates"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


# ── SLA Configuration ──────────────────────────────────────────────────────────

class SLAConfig(models.Model):
    """
    Per-role or per-stage SLA targets for time-to-fill and time-to-screen.
    Can be applied at job-family, job-level, or department scope.
    """

    SCOPE_CHOICES = [
        ("global", "Global (all roles)"),
        ("job_family", "Job Family"),
        ("job_level", "Job Level"),
        ("department", "Department"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sla_configs")
    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="global")
    job_family = models.ForeignKey(
        JobFamily, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sla_configs",
    )
    job_level = models.ForeignKey(
        JobLevel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sla_configs",
    )
    department = models.CharField(max_length=150, blank=True, default="")
    # Core SLA targets (in days)
    days_to_fill = models.IntegerField(default=45, help_text="Target days from open to hire")
    days_to_screen = models.IntegerField(default=5, help_text="Target days from apply to first screen")
    days_to_offer = models.IntegerField(default=30, help_text="Target days from open to offer")
    days_per_stage = models.JSONField(
        default=dict, blank=True,
        help_text='{"screening": 5, "interview": 14, "offer": 3} — max days per named stage',
    )
    escalation_enabled = models.BooleanField(default=True)
    escalation_recipient_role = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Role notified when SLA is breached (e.g. 'hiring_manager')",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sla_configs"
        ordering = ["scope", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_scope_display()})"


# ── Intake Meeting Templates ───────────────────────────────────────────────────

class IntakeMeetingTemplate(models.Model):
    """
    Reusable template for job intake meetings between recruiter and hiring manager.
    Provides pre-built question sets and agenda for standardised intake calls.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="intake_meeting_templates")
    name = models.CharField(max_length=255, help_text="e.g. 'Engineering IC Intake Template'")
    job_family = models.ForeignKey(
        JobFamily, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="intake_templates",
    )
    agenda_items = models.JSONField(
        default=list, blank=True,
        help_text='["Role overview & context", "Must-have skills", "Deal-breakers", "Interview process"]',
    )
    recruiter_questions = models.JSONField(
        default=list, blank=True,
        help_text='["What does success look like at 6 months?", "Why is the role open?"]',
    )
    must_have_prompt = models.TextField(
        blank=True, default="",
        help_text="Prompt text shown when capturing must-have requirements",
    )
    nice_to_have_prompt = models.TextField(
        blank=True, default="",
        help_text="Prompt text shown when capturing nice-to-have requirements",
    )
    suggested_pipeline = models.JSONField(
        default=list, blank=True,
        help_text='[{"round": 1, "type": "phone_screen", "duration_mins": 30}]',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "intake_meeting_templates"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


# ── Hiring Plan Calendar ───────────────────────────────────────────────────────

class HiringPlanCalendar(models.Model):
    """
    Maps headcount requisitions to calendar quarters/months with budget tracking.
    Enables quarter-by-quarter hiring plan views across departments.
    """

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("approved", "Approved"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("deferred", "Deferred"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hiring_plan_calendars")
    plan = models.ForeignKey(
        HeadcountPlan, on_delete=models.CASCADE, related_name="calendar_entries",
    )
    requisition = models.ForeignKey(
        HeadcountRequisition, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="calendar_entries",
    )
    fiscal_year = models.IntegerField()
    quarter = models.IntegerField(help_text="1–4")
    month = models.IntegerField(null=True, blank=True, help_text="1–12; optional month-level resolution")
    department = models.CharField(max_length=150, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    hiring_manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hiring_plan_entries",
    )
    target_start_date = models.DateField(null=True, blank=True)
    headcount = models.IntegerField(default=1, help_text="Number of seats in this entry")
    budget_allocated = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True,
        help_text="Budget allocated for this hire in the plan currency",
    )
    budget_currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hiring_plan_calendar"
        ordering = ["fiscal_year", "quarter", "department"]

    def __str__(self):
        return f"FY{self.fiscal_year} Q{self.quarter} — {self.department} ({self.headcount} seats)"
