"""CampusOS — Outcomes Analytics models."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class PlacementOutcome(TimestampedModel):
    """Final verified outcome for a placed student."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="placement_outcome")
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="placement_outcomes")
    academic_year = models.ForeignKey("campus.AcademicYear", on_delete=models.SET_NULL, null=True)
    program = models.ForeignKey("campus.Program", on_delete=models.SET_NULL, null=True)

    OUTCOME_CHOICES = [
        ("placed_campus_drive", "Placed via Campus Drive"),
        ("placed_off_campus", "Placed Off-Campus"),
        ("higher_education", "Pursuing Higher Education"),
        ("entrepreneurship", "Entrepreneurship"),
        ("government_exam", "Government Exam Preparation"),
        ("not_placed", "Not Placed"),
        ("opted_out", "Opted Out of Placement"),
        ("unknown", "Unknown"),
    ]

    outcome_type = models.CharField(max_length=30, choices=OUTCOME_CHOICES, default="unknown")
    employer_name = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    job_location = models.CharField(max_length=200, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    ctc_annual_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    offer_date = models.DateField(null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    is_dream_company = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_outcomes"
    )
    verification_document_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} — {self.outcome_type}"


class CohortOutcome(TimestampedModel):
    """Aggregated placement stats for a batch/program."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="cohort_outcomes")
    academic_year = models.ForeignKey("campus.AcademicYear", on_delete=models.CASCADE)
    department = models.ForeignKey("campus.Department", null=True, blank=True, on_delete=models.SET_NULL)
    program = models.ForeignKey("campus.Program", null=True, blank=True, on_delete=models.SET_NULL)

    # Counts
    total_eligible = models.PositiveIntegerField(default=0)
    total_registered = models.PositiveIntegerField(default=0)
    total_placed = models.PositiveIntegerField(default=0)
    total_higher_education = models.PositiveIntegerField(default=0)
    total_entrepreneurship = models.PositiveIntegerField(default=0)
    total_not_placed = models.PositiveIntegerField(default=0)

    # Salary stats (LKR)
    avg_ctc_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    median_ctc_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    highest_ctc_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    lowest_ctc_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # Ratios
    placement_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    computed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["campus", "academic_year", "program"]]
        ordering = ["-academic_year"]

    def __str__(self):
        return f"{self.campus} / {self.program} / {self.academic_year} — {self.placement_rate_pct}%"


class AlumniDestination(TimestampedModel):
    """Long-term tracking of alumni career trajectories."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alumni = models.ForeignKey("alumni_mentors.AlumniProfile", on_delete=models.CASCADE, related_name="career_milestones")
    employer = models.CharField(max_length=200)
    designation = models.CharField(max_length=200)
    industry = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Sri Lanka")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    annual_ctc_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]


class AccreditationReport(TimestampedModel):
    """Auto-generated accreditation readiness report."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="accreditation_reports")
    report_type = models.CharField(
        max_length=30,
        choices=[("naac", "NAAC"), ("nba", "NBA"), ("abet", ("ABET")), ("qs", "QS"), ("internal", "Internal")],
    )
    for_year = models.CharField(max_length=9, help_text="e.g. 2023-2024")
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    data_snapshot = models.JSONField(default=dict)
    is_finalized = models.BooleanField(default=False)
    pdf_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-generated_at"]


class EmployabilityTrendPoint(TimestampedModel):
    """Time-series employability readiness data for charting."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="trend_points")
    program = models.ForeignKey("campus.Program", null=True, blank=True, on_delete=models.SET_NULL)
    as_of_date = models.DateField()
    avg_readiness_score = models.DecimalField(max_digits=5, decimal_places=2)
    at_risk_count = models.PositiveIntegerField(default=0)
    high_performer_count = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [["campus", "program", "as_of_date"]]
        ordering = ["-as_of_date"]
