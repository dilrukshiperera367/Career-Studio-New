"""
CampusOS — Internships: Internship, Co-op, Apprenticeship, and Experiential Learning Management.

Models:
    InternshipOpportunity — posted internship/co-op listings
    InternshipApplication — student application to an opportunity
    InternshipRecord      — confirmed internship placement record
    InternshipLogbook     — student daily/weekly journal entries
    SupervisorEvaluation  — employer/supervisor evaluation
    TrainingAgreement     — formal training agreement documents
    ExperientialProgram   — live projects, capstones, externships
    ExperientialEnrollment — student enrollment in experiential program
"""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class InternshipOpportunity(TimestampedModel):
    """Internship, co-op, or apprenticeship opportunity posted to CampusOS."""

    class OpportunityType(models.TextChoices):
        INTERNSHIP = "internship", "Internship"
        CO_OP = "co_op", "Co-op"
        APPRENTICESHIP = "apprenticeship", "Apprenticeship"
        EXTERNSHIP = "externship", "Externship / Job Shadow"
        PRACTICUM = "practicum", "Practicum / Industrial Training"
        RESEARCH = "research", "Research Assistantship"
        LIVE_PROJECT = "live_project", "Live Project"
        CAPSTONE = "capstone", "Capstone Project"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Faculty Approval"
        OPEN = "open", "Open for Applications"
        CLOSED = "closed", "Closed"
        FILLED = "filled", "Filled"
        CANCELLED = "cancelled", "Cancelled"

    class WorkMode(models.TextChoices):
        ON_SITE = "on_site", "On-site"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="internship_opportunities"
    )
    employer = models.ForeignKey(
        "campus_employers.CampusEmployer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internship_opportunities",
    )
    # Allow non-CRM employers too
    employer_name = models.CharField(max_length=300, blank=True, default="")
    posted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="posted_internships",
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_internships",
    )

    opportunity_type = models.CharField(max_length=20, choices=OpportunityType.choices, default=OpportunityType.INTERNSHIP)
    title = models.CharField(max_length=300)
    description = models.TextField()
    responsibilities = models.TextField(blank=True, default="")
    required_skills = models.JSONField(default=list)
    preferred_skills = models.JSONField(default=list)
    learning_objectives = models.JSONField(default=list)

    # Eligibility
    eligible_programs = models.ManyToManyField(
        "campus.Program", blank=True, related_name="internship_opportunities"
    )
    min_year = models.PositiveSmallIntegerField(default=1)
    max_year = models.PositiveSmallIntegerField(default=4)
    min_cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    eligible_graduation_years = models.JSONField(default=list)

    # Logistics
    location_city = models.CharField(max_length=100, blank=True, default="")
    location_country = models.CharField(max_length=100, blank=True, default="Sri Lanka")
    work_mode = models.CharField(max_length=10, choices=WorkMode.choices, default=WorkMode.ON_SITE)
    duration_weeks = models.PositiveSmallIntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    openings = models.PositiveSmallIntegerField(default=1)

    # Compensation
    is_paid = models.BooleanField(default=False)
    stipend_monthly_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stipend_currency = models.CharField(max_length=5, default="LKR")
    benefits = models.JSONField(default=list)
    conversion_to_fulltime_possible = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_campus_exclusive = models.BooleanField(default=True)
    views_count = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "internship_opportunities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campus", "status", "opportunity_type"]),
        ]

    def __str__(self):
        employer = self.employer_name or (self.employer.name if self.employer else "Unknown")
        return f"{self.title} @ {employer}"


class InternshipApplication(TimestampedModel):
    """Student application to an internship opportunity."""

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
        OFFERED = "offered", "Offered"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(
        InternshipOpportunity, on_delete=models.CASCADE, related_name="applications"
    )
    student = models.ForeignKey(
        "students.StudentProfile", on_delete=models.CASCADE, related_name="internship_applications"
    )
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.APPLIED)
    cover_letter = models.TextField(blank=True, default="")
    resume_file = models.FileField(upload_to="internships/resumes/", null=True, blank=True)
    additional_docs = models.JSONField(default=list)

    # Faculty approval (if required)
    faculty_approved = models.BooleanField(null=True, blank=True)
    faculty_approver = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="internship_application_approvals",
    )
    faculty_notes = models.TextField(blank=True, default="")

    # Employer feedback
    employer_notes = models.TextField(blank=True, default="")
    interview_date = models.DateTimeField(null=True, blank=True)
    offer_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "internship_applications"
        unique_together = [["opportunity", "student"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.user.get_full_name()} → {self.opportunity.title}"


class InternshipRecord(TimestampedModel):
    """Confirmed internship placement — the live record tracking the actual experience."""

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ACTIVE = "active", "Active / Ongoing"
        COMPLETED = "completed", "Completed"
        DISCONTINUED = "discontinued", "Discontinued"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        InternshipApplication, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="record",
    )
    student = models.ForeignKey(
        "students.StudentProfile", on_delete=models.CASCADE, related_name="internship_records"
    )
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="internship_records"
    )
    employer_name = models.CharField(max_length=300)
    role_title = models.CharField(max_length=200)
    opportunity_type = models.CharField(
        max_length=20, choices=InternshipOpportunity.OpportunityType.choices
    )
    department_at_employer = models.CharField(max_length=200, blank=True, default="")
    supervisor_name = models.CharField(max_length=200, blank=True, default="")
    supervisor_email = models.EmailField(blank=True, default="")
    supervisor_phone = models.CharField(max_length=30, blank=True, default="")

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)

    # Compensation
    stipend_monthly_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_stipend_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Outcomes
    converted_to_fulltime = models.BooleanField(null=True, blank=True)
    fulltime_offer_package_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    fulltime_offer_accepted = models.BooleanField(null=True, blank=True)

    # Logistics
    work_mode = models.CharField(
        max_length=10, choices=InternshipOpportunity.WorkMode.choices, default="on_site"
    )
    location = models.CharField(max_length=200, blank=True, default="")

    # Learning agreement / faculty-signed docs
    training_agreement_signed = models.BooleanField(default=False)
    training_agreement_file = models.FileField(
        upload_to="internships/agreements/", null=True, blank=True
    )

    # Post-internship evidence capture
    completion_certificate = models.FileField(
        upload_to="internships/certificates/", null=True, blank=True
    )
    student_reflection = models.TextField(blank=True, default="")
    skills_gained = models.JSONField(default=list)

    class Meta:
        db_table = "internship_records"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.student.user.get_full_name()} @ {self.employer_name} ({self.status})"


class InternshipLogbook(TimestampedModel):
    """Student daily/weekly journal during their internship."""

    class EntryType(models.TextChoices):
        DAILY = "daily", "Daily Log"
        WEEKLY = "weekly", "Weekly Summary"
        MILESTONE = "milestone", "Milestone / Reflection"
        CHALLENGE = "challenge", "Challenge / Problem Solved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(
        InternshipRecord, on_delete=models.CASCADE, related_name="logbook_entries"
    )
    entry_type = models.CharField(max_length=15, choices=EntryType.choices, default=EntryType.DAILY)
    entry_date = models.DateField()
    title = models.CharField(max_length=300, blank=True, default="")
    content = models.TextField()
    hours_worked = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    tasks_completed = models.JSONField(default=list)
    skills_applied = models.JSONField(default=list)
    attachment = models.FileField(upload_to="internships/logbook/", null=True, blank=True)
    is_reviewed_by_supervisor = models.BooleanField(default=False)
    supervisor_feedback = models.TextField(blank=True, default="")

    class Meta:
        db_table = "internship_logbook"
        ordering = ["-entry_date"]


class SupervisorEvaluation(TimestampedModel):
    """Employer / supervisor evaluation at mid-point or end of internship."""

    class EvaluationPoint(models.TextChoices):
        MID_POINT = "mid_point", "Mid-point Review"
        END_POINT = "end_point", "End-point / Final Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(
        InternshipRecord, on_delete=models.CASCADE, related_name="evaluations"
    )
    evaluation_point = models.CharField(max_length=15, choices=EvaluationPoint.choices)
    evaluator_name = models.CharField(max_length=200)
    evaluator_email = models.EmailField(blank=True, default="")

    # Competency scores (keys mapped to NACE dimensions)
    scores = models.JSONField(
        default=dict,
        help_text="{competency_category: score_out_of_5}",
    )
    overall_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    strengths = models.TextField(blank=True, default="")
    areas_for_improvement = models.TextField(blank=True, default="")
    would_rehire = models.BooleanField(null=True, blank=True)
    recommendation = models.CharField(max_length=200, blank=True, default="")
    evaluation_file = models.FileField(upload_to="internships/evaluations/", null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "supervisor_evaluations"
        ordering = ["-created_at"]


class TrainingAgreement(TimestampedModel):
    """Formal training/MOU agreement for an internship."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT_TO_EMPLOYER = "sent_to_employer", "Sent to Employer"
        SIGNED_EMPLOYER = "signed_employer", "Signed by Employer"
        SIGNED_CAMPUS = "signed_campus", "Signed by Campus"
        FULLY_EXECUTED = "fully_executed", "Fully Executed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.OneToOneField(
        InternshipRecord, on_delete=models.CASCADE, related_name="training_agreement"
    )
    agreement_number = models.CharField(max_length=50, blank=True, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField()
    end_date = models.DateField()
    terms = models.TextField(blank=True, default="")
    employer_signatory_name = models.CharField(max_length=200, blank=True, default="")
    campus_signatory_name = models.CharField(max_length=200, blank=True, default="")
    signed_at = models.DateTimeField(null=True, blank=True)
    document_file = models.FileField(upload_to="internships/agreements/", null=True, blank=True)

    class Meta:
        db_table = "training_agreements"


class ExperientialProgram(TimestampedModel):
    """Live project, capstone, externship or shadowing program."""

    class ProgramType(models.TextChoices):
        LIVE_PROJECT = "live_project", "Live Industry Project"
        CAPSTONE = "capstone", "Capstone / Final Year Project"
        EXTERNSHIP = "externship", "Externship"
        JOB_SHADOW = "job_shadow", "Job Shadowing"
        COMMUNITY_PROJECT = "community_project", "Community / NGO Project"
        SIMULATION = "simulation", "Business Simulation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="experiential_programs"
    )
    title = models.CharField(max_length=300)
    program_type = models.CharField(max_length=20, choices=ProgramType.choices)
    description = models.TextField(blank=True, default="")
    partner_organization = models.CharField(max_length=300, blank=True, default="")
    faculty_lead = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="led_experiential_programs",
    )
    eligible_programs = models.ManyToManyField("campus.Program", blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    max_students = models.PositiveSmallIntegerField(default=30)
    learning_objectives = models.JSONField(default=list)
    deliverables = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "experiential_programs"
        ordering = ["-created_at"]


class ExperientialEnrollment(TimestampedModel):
    """Student enrollment in an experiential program."""

    class Status(models.TextChoices):
        ENROLLED = "enrolled", "Enrolled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        ExperientialProgram, on_delete=models.CASCADE, related_name="enrollments"
    )
    student = models.ForeignKey(
        "students.StudentProfile", on_delete=models.CASCADE, related_name="experiential_enrollments"
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ENROLLED)
    grade = models.CharField(max_length=20, blank=True, default="")
    faculty_notes = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_issued = models.BooleanField(default=False)

    class Meta:
        db_table = "experiential_enrollments"
        unique_together = [["program", "student"]]
