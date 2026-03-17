"""
CampusOS — Readiness: Career Readiness and Employability Engine.

Based on NACE career competency framework.

Competency dimensions:
    - Critical Thinking / Problem Solving
    - Oral / Written Communications
    - Teamwork / Collaboration
    - Digital Technology
    - Leadership / Project Management
    - Professionalism / Work Ethic
    - Career / Self Development
    - Equity / Inclusion

Models:
    ReadinessCompetency     — global competency definitions
    ReadinessAssessment     — one assessment event for a student
    CompetencyScore         — score per competency per assessment
    ReadinessBenchmark      — campus/program/cohort-level benchmarks
    ImprovementPlan         — personalized improvement plan
    ImprovementPlanTask     — individual tasks in a plan
    WeeklyCareerAction      — weekly action plans for students
    ReadinessGapAnalysis    — gap analysis snapshot
    PlacementRiskFlag       — placement-risk alerts
"""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class ReadinessCompetency(models.Model):
    """NACE-aligned or custom competency definition."""

    class Category(models.TextChoices):
        COMMUNICATION = "communication", "Communication"
        TEAMWORK = "teamwork", "Teamwork / Collaboration"
        CRITICAL_THINKING = "critical_thinking", "Critical Thinking"
        TECHNOLOGY = "technology", "Digital Technology"
        LEADERSHIP = "leadership", "Leadership"
        PROFESSIONALISM = "professionalism", "Professionalism"
        CAREER_DEVELOPMENT = "career_development", "Career & Self Development"
        EQUITY_INCLUSION = "equity_inclusion", "Equity & Inclusion"
        DOMAIN = "domain", "Domain / Technical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=25, choices=Category.choices)
    description = models.TextField(blank=True, default="")
    indicators = models.JSONField(
        default=list,
        help_text="List of observable behavioral indicators for this competency.",
    )
    is_nace_standard = models.BooleanField(default=False)
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00,
        help_text="Weighting in overall score calculation.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "readiness_competencies"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ReadinessAssessment(TimestampedModel):
    """A readiness assessment event for a student."""

    class AssessmentType(models.TextChoices):
        BASELINE = "baseline", "Baseline Diagnostic"
        SELF = "self", "Self-Assessment"
        FACULTY = "faculty", "Faculty / Advisor Assessment"
        EMPLOYER = "employer", "Employer Post-Internship Assessment"
        PEER = "peer", "Peer Assessment"
        SYSTEM = "system", "System-computed (profile-based)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="readiness_assessments",
    )
    assessment_type = models.CharField(max_length=15, choices=AssessmentType.choices)
    assessor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_assessments",
        help_text="Null = self-assessment or system-generated.",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)

    # Computed readiness score (0–100)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_label = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="e.g. Entry-Ready, Emerging, Developing, Career-Ready",
    )

    # Role-specific context
    target_role = models.CharField(max_length=200, blank=True, default="")
    target_industry = models.CharField(max_length=200, blank=True, default="")

    # Internship reference (for post-internship employer assessments)
    internship = models.ForeignKey(
        "internships.InternshipRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="readiness_assessments",
    )

    notes = models.TextField(blank=True, default="")
    assessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "readiness_assessments"
        ordering = ["-assessed_at"]

    def __str__(self):
        return f"{self.assessment_type} — {self.student.user.get_full_name()} ({self.overall_score})"

    def compute_overall_score(self):
        scores = self.competency_scores.select_related("competency")
        if not scores.exists():
            return 0
        total_weight = sum(s.competency.weight for s in scores)
        if total_weight == 0:
            return 0
        weighted = sum(float(s.score) * float(s.competency.weight) for s in scores)
        return round(weighted / float(total_weight), 2)


class CompetencyScore(models.Model):
    """Score for a specific competency within a readiness assessment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        ReadinessAssessment, on_delete=models.CASCADE, related_name="competency_scores"
    )
    competency = models.ForeignKey(
        ReadinessCompetency, on_delete=models.PROTECT, related_name="scores"
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Score 0–100.",
    )
    sub_scores = models.JSONField(
        default=dict,
        help_text="Per-indicator sub-scores {indicator: score}.",
    )
    evidence = models.TextField(blank=True, default="")
    improvement_notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "readiness_competency_scores"
        unique_together = [["assessment", "competency"]]

    def __str__(self):
        return f"{self.competency.name}: {self.score}"


class ReadinessBenchmark(TimestampedModel):
    """Campus / program / cohort aggregate readiness benchmarks."""

    class BenchmarkLevel(models.TextChoices):
        CAMPUS = "campus", "Campus-wide"
        PROGRAM = "program", "Program-level"
        COHORT = "cohort", "Cohort / Batch"
        DEPARTMENT = "department", "Department-level"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="readiness_benchmarks"
    )
    level = models.CharField(max_length=15, choices=BenchmarkLevel.choices)
    program = models.ForeignKey(
        "campus.Program", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="readiness_benchmarks",
    )
    department = models.ForeignKey(
        "campus.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="readiness_benchmarks",
    )
    cohort_year = models.PositiveSmallIntegerField(null=True, blank=True)
    academic_year = models.ForeignKey(
        "campus.AcademicYear", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="readiness_benchmarks",
    )

    avg_overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_competency_scores = models.JSONField(
        default=dict,
        help_text="{competency_id: avg_score}",
    )
    student_count = models.PositiveIntegerField(default=0)
    below_threshold_count = models.PositiveIntegerField(
        default=0, help_text="Students below readiness threshold."
    )
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "readiness_benchmarks"
        ordering = ["-computed_at"]

    def __str__(self):
        return f"Benchmark — {self.campus.name} / {self.level} ({self.avg_overall_score})"


class ImprovementPlan(TimestampedModel):
    """Personalized improvement plan for a student with gap analysis."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="improvement_plans",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_improvement_plans",
    )
    title = models.CharField(max_length=300)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    based_on_assessment = models.ForeignKey(
        ReadinessAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="improvement_plans",
    )
    target_score = models.DecimalField(max_digits=5, decimal_places=2, default=75.00)
    target_role = models.CharField(max_length=200, blank=True, default="")
    gap_summary = models.TextField(blank=True, default="")
    ai_generated_plan = models.BooleanField(
        default=False, help_text="Plan generated via AI copilot."
    )
    start_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_pct = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "readiness_improvement_plans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.student.user.get_full_name()}"


class ImprovementPlanTask(TimestampedModel):
    """Individual task / milestone within an improvement plan."""

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(ImprovementPlan, on_delete=models.CASCADE, related_name="tasks")
    competency = models.ForeignKey(
        ReadinessCompetency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="improvement_tasks",
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    resource_url = models.URLField(blank=True, default="")
    resource_type = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="e.g. video, article, workshop, assessment",
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.TODO)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "readiness_improvement_tasks"
        ordering = ["sort_order", "due_date"]


class WeeklyCareerAction(TimestampedModel):
    """Weekly career action plan entries for a student."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="weekly_actions",
    )
    week_start = models.DateField()
    actions = models.JSONField(
        default=list,
        help_text="[{action, completed, notes}]",
    )
    reflection = models.TextField(blank=True, default="")
    score_at_week_start = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = "student_weekly_career_actions"
        unique_together = [["student", "week_start"]]
        ordering = ["-week_start"]


class ReadinessGapAnalysis(models.Model):
    """Snapshot gap analysis between current scores and role-specific targets."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="gap_analyses",
    )
    assessment = models.ForeignKey(ReadinessAssessment, on_delete=models.CASCADE, related_name="gap_analyses")
    target_role = models.CharField(max_length=200, blank=True, default="")
    target_industry = models.CharField(max_length=200, blank=True, default="")
    gaps = models.JSONField(
        default=list,
        help_text="[{competency, current_score, target_score, gap, priority}]",
    )
    recommendations = models.JSONField(default=list)
    ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "readiness_gap_analyses"
        ordering = ["-created_at"]


class PlacementRiskFlag(TimestampedModel):
    """Placement risk flags for at-risk students."""

    class RiskType(models.TextChoices):
        LOW_READINESS = "low_readiness", "Low Readiness Score"
        INCOMPLETE_PROFILE = "incomplete_profile", "Incomplete Profile"
        LOW_APPLICATIONS = "low_applications", "Low Application Activity"
        POOR_ASSESSMENT = "poor_assessment", "Poor Assessment Performance"
        NO_PARTICIPATION = "no_participation", "Not Participating in Drives"
        LOW_CGPA = "low_cgpa", "Low CGPA (below placement threshold)"
        MISSING_SKILLS = "missing_skills", "Missing Key Skills"
        AT_RISK_GENERAL = "at_risk_general", "General At-Risk Flag"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress (Intervention Active)"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="risk_flags",
    )
    risk_type = models.CharField(max_length=25, choices=RiskType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    description = models.TextField(blank=True, default="")
    flagged_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="raised_risk_flags",
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_risk_flags",
    )
    resolution_notes = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "placement_risk_flags"
        ordering = ["-severity", "-created_at"]

    def __str__(self):
        return f"{self.risk_type} ({self.severity}) — {self.student.user.get_full_name()}"
