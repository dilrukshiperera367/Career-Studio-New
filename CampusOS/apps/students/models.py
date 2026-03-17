"""
CampusOS — Students: Student profiles, employability records, and profile management.

Models:
    StudentProfile      — extended profile beyond auth User
    EmployabilityProfile — target job preferences, visibility
    StudentEducation    — academic history (multiple institutions)
    StudentSkill        — skills with proficiency levels
    StudentProject      — academic/personal projects
    StudentCertification — certifications and licenses
    StudentLanguage     — language proficiencies
    StudentAchievement  — awards, competitions, publications
    StudentActivityLog  — timeline of platform activity
    CampusReadinessBadge — campus-issued readiness badges
"""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class StudentProfile(TimestampedModel):
    """Extended profile for student users, linked 1:1 to accounts.User."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        NON_BINARY = "non_binary", "Non-binary"
        PREFER_NOT = "prefer_not", "Prefer not to say"

    class PlacementEligibility(models.TextChoices):
        ELIGIBLE = "eligible", "Eligible"
        INELIGIBLE = "ineligible", "Ineligible"
        CONDITIONAL = "conditional", "Conditionally Eligible"
        PLACED = "placed", "Already Placed"
        NOT_SEEKING = "not_seeking", "Not Seeking Placement"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="student_profile"
    )
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="student_profiles"
    )
    program = models.ForeignKey(
        "campus.Program", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="students",
    )
    department = models.ForeignKey(
        "campus.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="students",
    )

    # Academic identity
    student_id = models.CharField(max_length=50, blank=True, default="")
    enrollment_year = models.PositiveSmallIntegerField(null=True, blank=True)
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    current_year = models.PositiveSmallIntegerField(default=1)
    current_semester = models.PositiveSmallIntegerField(default=1)
    specialization = models.CharField(max_length=200, blank=True, default="")
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    active_backlogs = models.PositiveSmallIntegerField(default=0)
    backlogs_history = models.PositiveSmallIntegerField(default=0)
    roll_number = models.CharField(max_length=50, blank=True, default="")

    # Personal
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=15, choices=Gender.choices, blank=True, default="")
    nationality = models.CharField(max_length=100, blank=True, default="")
    home_city = models.CharField(max_length=100, blank=True, default="")
    home_state = models.CharField(max_length=100, blank=True, default="")
    home_country = models.CharField(max_length=100, blank=True, default="Sri Lanka")

    # Work authorization
    work_authorization = models.CharField(max_length=200, blank=True, default="")
    visa_status = models.CharField(max_length=100, blank=True, default="")
    willing_to_relocate = models.BooleanField(default=True)
    relocation_preferences = models.JSONField(
        default=list, help_text="List of preferred cities/countries for relocation."
    )

    # Placement
    placement_eligibility = models.CharField(
        max_length=20, choices=PlacementEligibility.choices, default=PlacementEligibility.ELIGIBLE
    )
    placement_eligibility_notes = models.TextField(blank=True, default="")
    placed_at_company = models.CharField(max_length=300, blank=True, default="")
    placed_package_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    placement_date = models.DateField(null=True, blank=True)

    # Campus-specific profile URL
    profile_slug = models.SlugField(max_length=100, unique=True, blank=True)

    # Profile completeness (0-100, computed)
    profile_completion_pct = models.PositiveSmallIntegerField(default=0)

    # Visibility
    profile_public = models.BooleanField(default=False)
    show_to_employers = models.BooleanField(default=True)
    show_cgpa = models.BooleanField(default=True)

    class Meta:
        db_table = "student_profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campus", "placement_eligibility"]),
            models.Index(fields=["campus", "program", "current_year"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.campus.short_name or self.campus.name})"

    def compute_completion(self):
        """Compute profile completion percentage."""
        fields = [
            bool(self.date_of_birth), bool(self.gender),
            bool(self.cgpa is not None), bool(self.program_id),
            self.user.profile_photo is not None,
            bool(self.user.phone),
        ]
        filled = sum(fields)
        skills = self.skills.count() > 0
        edu = self.educations.count() > 0
        return min(100, int((filled + skills + edu) / (len(fields) + 2) * 100))


class EmployabilityProfile(TimestampedModel):
    """Career preferences and job targets."""

    class JobType(models.TextChoices):
        INTERNSHIP = "internship", "Internship"
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        APPRENTICESHIP = "apprenticeship", "Apprenticeship"
        CO_OP = "co_op", "Co-op"
        FREELANCE = "freelance", "Freelance / Gig"

    class WorkMode(models.TextChoices):
        ON_SITE = "on_site", "On-site"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"
        FLEXIBLE = "flexible", "Flexible"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        StudentProfile, on_delete=models.CASCADE, related_name="employability_profile"
    )

    # Job targets
    target_roles = models.JSONField(default=list, help_text="List of target job titles.")
    target_industries = models.JSONField(default=list)
    target_companies = models.JSONField(default=list)
    target_cities = models.JSONField(default=list)
    target_countries = models.JSONField(default=list)

    # Preferences
    preferred_job_types = models.JSONField(default=list)
    preferred_work_mode = models.CharField(
        max_length=15, choices=WorkMode.choices, default=WorkMode.HYBRID
    )
    earliest_start_date = models.DateField(null=True, blank=True)

    # Salary expectations
    min_salary_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    max_salary_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    salary_negotiable = models.BooleanField(default=True)
    salary_currency = models.CharField(max_length=5, default="LKR")

    # Links
    linkedin_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")
    portfolio_url = models.URLField(blank=True, default="")
    behance_url = models.URLField(blank=True, default="")
    other_links = models.JSONField(default=list, help_text="[{label, url}]")

    # Summary / headline
    professional_summary = models.TextField(blank=True, default="", max_length=1000)
    elevator_pitch = models.TextField(blank=True, default="", max_length=300)

    # Readiness flags
    resume_ready = models.BooleanField(default=False)
    interview_ready = models.BooleanField(default=False)
    actively_seeking = models.BooleanField(default=True)

    class Meta:
        db_table = "student_employability_profiles"

    def __str__(self):
        return f"Employability — {self.student.user.get_full_name()}"


class StudentEducation(TimestampedModel):
    """Academic history — previous institutions, grades, degrees."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="educations"
    )
    institution_name = models.CharField(max_length=300)
    degree = models.CharField(max_length=200, blank=True, default="")
    field_of_study = models.CharField(max_length=200, blank=True, default="")
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    grade = models.CharField(max_length=30, blank=True, default="")
    activities = models.TextField(blank=True, default="")
    is_primary = models.BooleanField(
        default=False, help_text="Mark as the primary/current program."
    )

    class Meta:
        db_table = "student_educations"
        ordering = ["-start_year"]

    def __str__(self):
        return f"{self.degree} — {self.institution_name}"


class StudentSkill(TimestampedModel):
    """Skills with proficiency levels."""

    class Proficiency(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        EXPERT = "expert", "Expert"

    class SkillType(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        SOFT = "soft", "Soft Skill"
        LANGUAGE = "language", "Programming Language"
        TOOL = "tool", "Tool / Software"
        DOMAIN = "domain", "Domain Knowledge"
        CERTIFICATION = "certification", "Certification-backed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="skills"
    )
    name = models.CharField(max_length=100)
    skill_type = models.CharField(max_length=15, choices=SkillType.choices, default=SkillType.TECHNICAL)
    proficiency = models.CharField(max_length=15, choices=Proficiency.choices, default=Proficiency.INTERMEDIATE)
    years_of_experience = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    is_verified = models.BooleanField(
        default=False, help_text="Verified via assessment or credential."
    )
    endorsement_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "student_skills"
        unique_together = [["student", "name"]]
        ordering = ["-endorsement_count", "name"]

    def __str__(self):
        return f"{self.name} ({self.proficiency}) — {self.student.user.get_full_name()}"


class StudentProject(TimestampedModel):
    """Academic and personal projects."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="projects"
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    role = models.CharField(max_length=100, blank=True, default="")
    technologies = models.JSONField(default=list)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_ongoing = models.BooleanField(default=False)
    project_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")
    media_url = models.URLField(blank=True, default="")
    is_team_project = models.BooleanField(default=False)
    team_size = models.PositiveSmallIntegerField(null=True, blank=True)
    ai_generated_bullets = models.JSONField(
        default=list, help_text="AI-generated bullet points for resume."
    )
    is_capstone = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    class Meta:
        db_table = "student_projects"
        ordering = ["-is_featured", "-start_date"]

    def __str__(self):
        return f"{self.title} — {self.student.user.get_full_name()}"


class StudentCertification(TimestampedModel):
    """Certifications and professional licenses."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=300)
    issuing_organization = models.CharField(max_length=300)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    does_not_expire = models.BooleanField(default=False)
    credential_id = models.CharField(max_length=200, blank=True, default="")
    credential_url = models.URLField(blank=True, default="")
    certificate_file = models.FileField(
        upload_to="students/certifications/", null=True, blank=True
    )
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "student_certifications"
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.name} — {self.issuing_organization}"


class StudentLanguage(TimestampedModel):
    """Language proficiencies."""

    class Proficiency(models.TextChoices):
        ELEMENTARY = "elementary", "Elementary"
        LIMITED = "limited", "Limited Working"
        PROFESSIONAL = "professional", "Professional Working"
        FULL_PROFESSIONAL = "full_professional", "Full Professional"
        NATIVE = "native", "Native / Bilingual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="languages"
    )
    language = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=Proficiency.choices)
    is_native = models.BooleanField(default=False)

    class Meta:
        db_table = "student_languages"
        unique_together = [["student", "language"]]


class StudentAchievement(TimestampedModel):
    """Awards, competitions, publications, volunteer work."""

    class AchievementType(models.TextChoices):
        AWARD = "award", "Award / Honor"
        COMPETITION = "competition", "Competition / Hackathon"
        PUBLICATION = "publication", "Publication / Research"
        VOLUNTEER = "volunteer", "Volunteer Work"
        EXTRACURRICULAR = "extracurricular", "Extracurricular Activity"
        SCHOLARSHIP = "scholarship", "Scholarship / Fellowship"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="achievements"
    )
    title = models.CharField(max_length=300)
    achievement_type = models.CharField(max_length=20, choices=AchievementType.choices)
    issuing_organization = models.CharField(max_length=300, blank=True, default="")
    description = models.TextField(blank=True, default="")
    date = models.DateField(null=True, blank=True)
    url = models.URLField(blank=True, default="")
    is_featured = models.BooleanField(default=False)

    class Meta:
        db_table = "student_achievements"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.title} ({self.achievement_type}) — {self.student.user.get_full_name()}"


class StudentActivityLog(models.Model):
    """Immutable timeline of student platform activity for advisors and analytics."""

    class EventType(models.TextChoices):
        PROFILE_UPDATED = "profile_updated", "Profile Updated"
        RESUME_SENT = "resume_sent", "Resume Sent to CareerOS"
        APPLICATION_SUBMITTED = "application_submitted", "Application Submitted"
        INTERNSHIP_STARTED = "internship_started", "Internship Started"
        INTERNSHIP_COMPLETED = "internship_completed", "Internship Completed"
        ASSESSMENT_TAKEN = "assessment_taken", "Assessment Taken"
        PLACEMENT_REGISTERED = "placement_registered", "Registered for Drive"
        OFFER_RECEIVED = "offer_received", "Offer Received"
        OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
        MENTOR_CONNECTED = "mentor_connected", "Connected with Mentor"
        BADGE_EARNED = "badge_earned", "Badge / Credential Earned"
        EVENT_ATTENDED = "event_attended", "Event Attended"
        READINESS_IMPROVED = "readiness_improved", "Readiness Score Improved"
        WORKSHOP_COMPLETED = "workshop_completed", "Workshop Completed"
        ADVISOR_NOTE = "advisor_note", "Advisor Note Added"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="activity_logs"
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="logged_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_activity_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} — {self.student.user.get_full_name()}"


class CampusReadinessBadge(TimestampedModel):
    """Badges issued by campus staff for readiness milestones."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="campus_badges"
    )
    badge_name = models.CharField(max_length=200)
    badge_description = models.TextField(blank=True, default="")
    badge_image = models.ImageField(upload_to="students/badges/", null=True, blank=True)
    issued_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_badges",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    evidence_url = models.URLField(blank=True, default="")
    is_public = models.BooleanField(default=True)

    class Meta:
        db_table = "student_campus_badges"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.badge_name} — {self.student.user.get_full_name()}"
