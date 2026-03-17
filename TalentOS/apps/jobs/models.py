"""Jobs app — Job postings, pipeline stages, and templates."""

import uuid
from django.db import models
from apps.shared.html_sanitizer import sanitize_html


class Job(models.Model):
    """A job posting belonging to a tenant."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("paused", "Paused"),
        ("closed", "Closed"),
        ("archived", "Archived"),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ("full_time", "Full-time"),
        ("part_time", "Part-time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("temporary", "Temporary"),
    ]

    PRIORITY_CHOICES = [
        ("critical", "Critical"),
        ("high", "High"),
        ("normal", "Normal"),
        ("low", "Low"),
    ]

    REQUISITION_TYPE_CHOICES = [
        ("standard", "Standard"),
        ("internal_only", "Internal Only"),
        ("external_only", "External Only"),
        ("confidential", "Confidential"),
        ("evergreen", "Evergreen / Always-Open"),
        ("pooled", "Pooled / Talent Pool"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    department = models.CharField(max_length=150, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    is_remote = models.BooleanField(default=False)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default="full_time")
    description = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="USD")
    # Pay transparency (EU/US state laws)
    salary_disclosed = models.BooleanField(default=False, help_text="Show salary band on public posting")
    pay_frequency = models.CharField(
        max_length=20,
        choices=[("annual", "Annual"), ("monthly", "Monthly"), ("hourly", "Hourly")],
        default="annual",
    )
    # Degree-optional / skills-first hiring
    degree_required = models.BooleanField(default=False)
    degree_optional_note = models.TextField(blank=True, default="",
        help_text="Message shown to candidates: 'Degree not required — skills matter'")
    # Requisition type
    requisition_type = models.CharField(
        max_length=20, choices=REQUISITION_TYPE_CHOICES, default="standard",
        help_text="Controls visibility and pooling behaviour",
    )
    # Must-have vs trainable skill classification
    must_have_skills = models.JSONField(
        default=list, blank=True,
        help_text='[{"name": "Python", "level": "practitioner"}] — non-negotiable requirements'
    )
    trainable_skills = models.JSONField(
        default=list, blank=True,
        help_text='[{"name": "Docker"}] — nice-to-have; can be learned on the job'
    )
    # Hiring team (recruiter, coordinator, interviewers)
    hiring_team = models.JSONField(
        default=list, blank=True,
        help_text='[{"user_id": "...", "role": "recruiter|coordinator|interviewer"}]'
    )
    # SLA targets
    sla_days_to_fill = models.IntegerField(
        null=True, blank=True, help_text="Target days from open to hire"
    )
    sla_days_to_screen = models.IntegerField(
        null=True, blank=True, help_text="Target days from apply to first screen"
    )
    # Hiring calendar
    target_start_date = models.DateField(null=True, blank=True)
    # JD quality & inclusive language
    jd_quality_score = models.FloatField(
        null=True, blank=True, help_text="0–100 quality score from last JD scan"
    )
    inclusive_language_score = models.FloatField(
        null=True, blank=True, help_text="0–100 inclusive language score from last scan"
    )
    inclusive_language_flags = models.JSONField(
        default=list, blank=True,
        help_text='[{"term": "ninja", "suggestion": "engineer", "severity": "medium"}]'
    )
    # Headcount planning FK to job_architecture
    headcount_plan = models.ForeignKey(
        "job_architecture.HeadcountPlan",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="jobs",
    )
    # Job architecture / level
    job_level = models.ForeignKey(
        "job_architecture.JobLevel",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="jobs",
    )
    job_family = models.ForeignKey(
        "job_architecture.JobFamily",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="jobs",
    )

    # Matching config
    required_skills = models.JSONField(
        default=list, blank=True,
        help_text='[{"skill_id": "...", "name": "...", "weight": 1.0, "required": true}]'
    )
    optional_skills = models.JSONField(default=list, blank=True)
    target_titles = models.JSONField(default=list, blank=True, help_text="List of canonical job titles")
    min_years_experience = models.FloatField(null=True, blank=True)
    max_years_experience = models.FloatField(null=True, blank=True)
    domain_tags = models.JSONField(default=list, blank=True)
    screening_questions = models.JSONField(
        default=list, blank=True,
        help_text='[{"question": "...", "type": "boolean|text", "knockout": true, "knockout_value": false, "score_weight": 1}]'
    )

    # Enhanced fields (Features 23-38)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="normal")
    internal_only = models.BooleanField(default=False, help_text="Only visible to current employees")
    application_deadline = models.DateTimeField(null=True, blank=True)
    requisition_id = models.CharField(max_length=100, blank=True, default="", help_text="External HRIS job code")
    headcount_target = models.IntegerField(default=1)
    headcount_filled = models.IntegerField(default=0)
    template_source = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Job template this was cloned from"
    )
    locations = models.JSONField(default=list, blank=True, help_text="Multi-location support")
    view_count = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="created_jobs"
    )
    hiring_manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_jobs"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "priority"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.tenant.name})"

    def save(self, *args, **kwargs):
        # Sanitize HTML in user-written fields
        if self.description:
            self.description = sanitize_html(self.description)
        if self.requirements:
            self.requirements = sanitize_html(self.requirements)
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete_many([
            f'jobs:list:{self.tenant_id}',
            f'dashboard:{self.tenant_id}',
        ])


class JobTemplate(models.Model):
    """Reusable job posting template — clone to create new jobs instantly."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_templates")
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=150, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    employment_type = models.CharField(max_length=20, default="full_time")
    description = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    required_skills = models.JSONField(default=list, blank=True)
    optional_skills = models.JSONField(default=list, blank=True)
    target_titles = models.JSONField(default=list, blank=True)
    screening_questions = models.JSONField(default=list, blank=True)
    pipeline_stages = models.JSONField(default=list, blank=True,
        help_text='[{"name": "Applied", "stage_type": "applied", "order": 1}]')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_templates"

    def __str__(self):
        return f"Template: {self.name}"


class PipelineStage(models.Model):
    """Stage in a job's recruitment pipeline."""

    STAGE_TYPE_CHOICES = [
        ("applied", "Applied"),
        ("screening", "Screening"),
        ("interview", "Interview"),
        ("assessment", "Assessment"),
        ("offer", "Offer"),
        ("hired", "Hired"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="pipeline_stages")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="pipeline_stages")
    name = models.CharField(max_length=100)
    stage_type = models.CharField(max_length=20, choices=STAGE_TYPE_CHOICES, default="custom")
    order = models.IntegerField(default=0)
    is_terminal = models.BooleanField(default=False)
    auto_actions = models.JSONField(default=list, blank=True, help_text="Actions triggered on stage entry")

    # SLA & checklist (Features 26, 143, 150)
    sla_days = models.IntegerField(null=True, blank=True, help_text="Max days in this stage")
    stage_checklist = models.JSONField(default=list, blank=True,
        help_text='["Resume reviewed", "Phone screen done", "References checked"]')
    notes_template = models.TextField(blank=True, default="",
        help_text="Pre-filled notes template when entering this stage")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pipeline_stages"
        ordering = ["order"]
        unique_together = [("job", "order")]

    def __str__(self):
        return f"{self.name} (#{self.order}) — {self.job.title}"


class JobIntakeMeeting(models.Model):
    """
    Records a job intake meeting between recruiter and hiring manager.
    Captures agreed-upon requirements before the role goes live.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_intake_meetings")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="intake_meetings")
    recruiter = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="intake_meetings_as_recruiter",
    )
    hiring_manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="intake_meetings_as_hm",
    )
    meeting_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    agreed_requirements = models.JSONField(
        default=dict, blank=True,
        help_text='{"must_have": [...], "nice_to_have": [...], "deal_breakers": [...]}'
    )
    interview_process = models.JSONField(
        default=list, blank=True,
        help_text='[{"round": 1, "type": "phone", "interviewer": "...", "duration_mins": 30}]'
    )
    target_start_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_intake_meetings"
        ordering = ["-meeting_date"]

    def __str__(self):
        return f"Intake: {self.job.title} on {self.meeting_date}"
