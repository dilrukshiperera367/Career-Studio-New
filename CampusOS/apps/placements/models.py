"""
CampusOS — Placements: Campus Placement Drive Management.

Models:
    PlacementSeason     — annual placement season record
    PlacementDrive      — company drive hosted on campus
    DriveEligibilityRule — eligibility criteria per drive
    StudentDriveRegistration — student registers for a drive
    DriveSlot           — test/interview slot
    DriveOffer          — offer extended to a student
    PlacementPolicy     — campus placement policy configuration
"""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class PlacementSeason(TimestampedModel):
    """Annual placement season — the master container for all drives."""

    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="placement_seasons"
    )
    academic_year = models.ForeignKey(
        "campus.AcademicYear", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="placement_seasons",
    )
    name = models.CharField(max_length=100, help_text="e.g. Placement Season 2025–26")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PLANNING)
    season_start = models.DateField()
    season_end = models.DateField()
    target_placement_count = models.PositiveIntegerField(default=0)
    eligible_batch_years = models.JSONField(default=list)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "placement_seasons"
        ordering = ["-season_start"]

    def __str__(self):
        return f"{self.name} — {self.campus.name}"


class PlacementDrive(TimestampedModel):
    """A company recruitment drive hosted on campus."""

    class DriveType(models.TextChoices):
        ON_CAMPUS = "on_campus", "On-Campus Drive"
        OFF_CAMPUS = "off_campus", "Off-Campus Drive"
        POOL_CAMPUS = "pool_campus", "Pool Campus Drive"
        VIRTUAL = "virtual", "Virtual Drive"
        DAY_ZERO = "day_zero", "Day Zero / Super Day"
        WALK_IN = "walk_in", "Walk-in Drive"

    class Status(models.TextChoices):
        ANNOUNCED = "announced", "Announced"
        OPEN = "open", "Open for Registration"
        SHORTLISTING = "shortlisting", "Shortlisting in Progress"
        TESTING = "testing", "Test / Screening Round"
        INTERVIEWING = "interviewing", "Interviews in Progress"
        OFFER_STAGE = "offer_stage", "Offer Stage"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    season = models.ForeignKey(
        PlacementSeason, on_delete=models.CASCADE, related_name="drives"
    )
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="placement_drives"
    )
    employer = models.ForeignKey(
        "campus_employers.CampusEmployer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="placement_drives",
    )
    company_name = models.CharField(max_length=300)
    company_logo = models.ImageField(upload_to="placements/company_logos/", null=True, blank=True)
    role_title = models.CharField(max_length=300)
    drive_type = models.CharField(max_length=15, choices=DriveType.choices, default=DriveType.ON_CAMPUS)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ANNOUNCED)

    # JD and role details
    job_description = models.TextField(blank=True, default="")
    required_skills = models.JSONField(default=list)
    preferred_skills = models.JSONField(default=list)
    job_location = models.CharField(max_length=200, blank=True, default="")
    work_mode = models.CharField(
        max_length=15,
        choices=[("on_site", "On-site"), ("remote", "Remote"), ("hybrid", "Hybrid")],
        default="on_site",
    )

    # Compensation
    ctc_min_lkr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ctc_max_lkr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ctc_disclosed = models.BooleanField(default=True)
    benefits = models.JSONField(default=list)
    bond_required = models.BooleanField(default=False)
    bond_duration_months = models.PositiveSmallIntegerField(default=0)

    # Openings
    openings = models.PositiveSmallIntegerField(default=1)
    total_offers = models.PositiveSmallIntegerField(default=0)
    accepted_offers = models.PositiveSmallIntegerField(default=0)

    # Timeline
    drive_date = models.DateField(null=True, blank=True)
    registration_deadline = models.DateField(null=True, blank=True)
    offer_date = models.DateField(null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)

    # Selection process
    selection_rounds = models.JSONField(
        default=list,
        help_text="[{round_name, round_type, description}]",
    )

    # Placement policy overrides
    allow_multiple_offers = models.BooleanField(default=False)
    is_dream_company = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_drives",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "placement_drives"
        ordering = ["-drive_date", "-created_at"]

    def __str__(self):
        return f"{self.company_name} — {self.role_title} ({self.status})"


class DriveEligibilityRule(models.Model):
    """Eligibility rules per drive — GPA, program, year, backlog restrictions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drive = models.OneToOneField(
        PlacementDrive, on_delete=models.CASCADE, related_name="eligibility_rule"
    )
    eligible_programs = models.ManyToManyField("campus.Program", blank=True)
    eligible_departments = models.ManyToManyField("campus.Department", blank=True)
    min_cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    max_active_backlogs = models.PositiveSmallIntegerField(default=0)
    max_backlog_history = models.PositiveSmallIntegerField(default=0)
    min_year = models.PositiveSmallIntegerField(default=1)
    max_year = models.PositiveSmallIntegerField(default=4)
    eligible_graduation_years = models.JSONField(default=list)
    required_skills = models.JSONField(default=list)
    additional_criteria = models.TextField(blank=True, default="")
    custom_filters = models.JSONField(default=dict)

    class Meta:
        db_table = "drive_eligibility_rules"


class StudentDriveRegistration(TimestampedModel):
    """Student registration for a placement drive."""

    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED_SCREENING = "rejected_screening", "Not Shortlisted"
        TEST_SCHEDULED = "test_scheduled", "Test Scheduled"
        TEST_PASSED = "test_passed", "Test Passed"
        TEST_FAILED = "test_failed", "Test Failed"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
        OFFERED = "offered", "Offer Received"
        OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
        OFFER_REJECTED = "offer_rejected", "Offer Rejected"
        WAITLISTED = "waitlisted", "Waitlisted"
        NO_SHOW = "no_show", "No Show"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drive = models.ForeignKey(
        PlacementDrive, on_delete=models.CASCADE, related_name="registrations"
    )
    student = models.ForeignKey(
        "students.StudentProfile", on_delete=models.CASCADE, related_name="drive_registrations"
    )
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.REGISTERED)
    registration_number = models.CharField(max_length=50, blank=True, default="")
    is_eligible = models.BooleanField(default=True)
    eligibility_override_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="eligibility_overrides",
    )
    eligibility_override_reason = models.TextField(blank=True, default="")
    shortlisted_at = models.DateTimeField(null=True, blank=True)
    placement_officer_notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "student_drive_registrations"
        unique_together = [["drive", "student"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.user.get_full_name()} — {self.drive.company_name} ({self.status})"


class DriveSlot(TimestampedModel):
    """Test or interview slot for a drive."""

    class SlotType(models.TextChoices):
        TEST = "test", "Written / Online Test"
        TECHNICAL_INTERVIEW = "technical_interview", "Technical Interview"
        HR_INTERVIEW = "hr_interview", "HR Interview"
        GROUP_DISCUSSION = "group_discussion", "Group Discussion"
        PRESENTATION = "presentation", "Presentation"
        ASSESSMENT_CENTER = "assessment_center", "Assessment Center"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drive = models.ForeignKey(PlacementDrive, on_delete=models.CASCADE, related_name="slots")
    slot_type = models.CharField(max_length=25, choices=SlotType.choices)
    round_number = models.PositiveSmallIntegerField(default=1)
    slot_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=300, blank=True, default="")
    panel_members = models.JSONField(default=list)
    max_capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    booked_count = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "drive_slots"
        ordering = ["slot_date", "start_time"]


class DriveOffer(TimestampedModel):
    """Offer extended to a student through a placement drive."""

    class Status(models.TextChoices):
        EXTENDED = "extended", "Offer Extended"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        DEFERRED = "deferred", "Deferred"
        LAPSED = "lapsed", "Lapsed / Expired"
        REVOKED = "revoked", "Revoked by Employer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.OneToOneField(
        StudentDriveRegistration, on_delete=models.CASCADE, related_name="offer"
    )
    drive = models.ForeignKey(
        PlacementDrive, on_delete=models.CASCADE, related_name="offers"
    )
    student = models.ForeignKey(
        "students.StudentProfile", on_delete=models.CASCADE, related_name="placement_offers"
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.EXTENDED)

    offer_letter = models.FileField(upload_to="placements/offers/", null=True, blank=True)
    role_title = models.CharField(max_length=300)
    location = models.CharField(max_length=200, blank=True, default="")
    joining_date = models.DateField(null=True, blank=True)

    ctc_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    ctc_breakdown = models.JSONField(default=dict, help_text="{base, variable, bonus, other}")

    offer_acceptance_deadline = models.DateField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    # Anti-duplication: tracks if student has other offers
    other_offers_count = models.PositiveSmallIntegerField(default=0)
    is_final_offer = models.BooleanField(
        default=False, help_text="Final/placed offer in one-offer-per-student policy."
    )

    class Meta:
        db_table = "drive_offers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Offer: {self.student.user.get_full_name()} ← {self.drive.company_name} ({self.status})"
