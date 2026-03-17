"""
MarketplaceOS — apps.learning_marketplace

Learning Marketplace — courses, cohort programs, bootcamps, certifications.

Models:
    Course              — Learning course/program listing
    CourseModule        — Top-level module in a course
    CourseLesson        — Individual lesson within a module
    CourseEnrollment    — Buyer's enrollment in a course
    CourseCompletion    — Completion record & certificate issuance
    CohortProgram       — Cohort/bootcamp cohort-based program
    CohortEnrollment    — Participant enrollment in a cohort program
    CohortSession       — Individual session/class in a cohort program
    CourseLearningPath  — Curated learning path (sequence of courses)
"""
import uuid
from django.db import models
from django.conf import settings


class Course(models.Model):
    """
    Learning course, cohort program, bootcamp, or certification prep offering.
    Covers live workshops, pre-recorded courses, certification tracks and more.
    """

    class CourseType(models.TextChoices):
        LIVE_COURSE = "live", "Live Online Course"
        RECORDED = "recorded", "Pre-Recorded Course"
        COHORT = "cohort", "Cohort Program"
        BOOTCAMP = "bootcamp", "Bootcamp"
        WORKSHOP = "workshop", "Workshop / Webinar"
        CERTIFICATION = "certification", "Certification Prep"
        PATHWAY = "pathway", "Learning Pathway"
        OFFICE_HOURS = "office_hours", "Office Hours"

    class CourseStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"
        COMING_SOON = "coming_soon", "Coming Soon"

    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        ALL_LEVELS = "all_levels", "All Levels"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="courses",
    )
    category = models.ForeignKey(
        "services_catalog.ServiceCategory", on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    course_type = models.CharField(max_length=15, choices=CourseType.choices)
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300)
    short_description = models.CharField(max_length=400, blank=True, default="")
    description = models.TextField()
    difficulty_level = models.CharField(max_length=15, choices=DifficultyLevel.choices, default=DifficultyLevel.ALL_LEVELS)
    status = models.CharField(max_length=15, choices=CourseStatus.choices, default=CourseStatus.DRAFT)

    # Delivery
    duration_hours = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    session_count = models.IntegerField(null=True, blank=True)
    max_seats = models.IntegerField(null=True, blank=True, help_text="Null = unlimited.")
    languages = models.JSONField(default=list)

    # Pricing
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, default="LKR")
    is_free = models.BooleanField(default=False)

    # SEO & discoverability
    tags = models.JSONField(default=list)
    skills_covered = models.JSONField(default=list)
    target_roles = models.JSONField(default=list)
    industries = models.JSONField(default=list)
    prerequisites = models.JSONField(default=list)
    learning_outcomes = models.JSONField(default=list)
    certificate_awarded = models.BooleanField(default=False)

    # Enterprise
    enterprise_only = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    # Denormalized stats
    total_enrollments = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    thumbnail_url = models.URLField(blank=True, default="")
    intro_video_url = models.URLField(blank=True, default="")
    syllabus_url = models.URLField(blank=True, default="")

    next_start_date = models.DateTimeField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_course"
        ordering = ["-created_at"]
        unique_together = [["provider", "slug"]]

    def __str__(self):
        return f"{self.title} ({self.get_course_type_display()})"


class CourseModule(models.Model):
    """Top-level module/section in a course curriculum."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mp_course_module"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.course.title} — {self.title}"


class CourseLesson(models.Model):
    """Individual lesson/class within a module."""

    class LessonType(models.TextChoices):
        VIDEO = "video", "Video"
        LIVE_SESSION = "live", "Live Session"
        READING = "reading", "Reading"
        QUIZ = "quiz", "Quiz"
        ASSIGNMENT = "assignment", "Assignment"
        DOWNLOAD = "download", "Downloadable Resource"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name="lessons")
    lesson_type = models.CharField(max_length=15, choices=LessonType.choices)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    content_url = models.URLField(blank=True, default="")
    duration_minutes = models.IntegerField(null=True, blank=True)
    is_preview = models.BooleanField(default=False, help_text="Free preview lesson.")
    sort_order = models.IntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True,
                                         help_text="For live sessions: scheduled start time.")

    class Meta:
        db_table = "mp_course_lesson"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.module.title} — {self.title}"


class CourseEnrollment(models.Model):
    """Buyer's enrollment in a course."""

    class EnrollmentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_enrollments")
    payment = models.ForeignKey("payments.Payment", on_delete=models.SET_NULL, null=True, blank=True)
    enterprise_account = models.ForeignKey(
        "enterprise_marketplace.EnterpriseAccount", on_delete=models.SET_NULL, null=True, blank=True,
    )
    status = models.CharField(max_length=15, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE)
    progress_pct = models.IntegerField(default=0, help_text="0–100 percent completion.")
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_course_enrollment"
        unique_together = [["course", "learner"]]
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.learner.email} → {self.course.title} ({self.status})"


class CourseCompletion(models.Model):
    """Completion record and certificate issuance for a course."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.OneToOneField(CourseEnrollment, on_delete=models.CASCADE, related_name="completion")
    certificate_url = models.URLField(blank=True, default="")
    certificate_id = models.CharField(max_length=50, blank=True, default="")
    completed_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "mp_course_completion"

    def __str__(self):
        return f"Certificate — {self.enrollment}"


class CohortProgram(models.Model):
    """
    Cohort-based program: a fixed group of learners progressing together.
    Used for bootcamps, interview sprints, cohort learning programs.
    """

    class CohortStatus(models.TextChoices):
        OPEN = "open", "Open — Accepting Applications"
        FULL = "full", "Full"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="cohorts")
    name = models.CharField(max_length=200, help_text="e.g. Cohort 1 — January 2025")
    facilitator = models.ForeignKey(
        "providers.Provider", on_delete=models.SET_NULL, null=True,
        related_name="facilitated_cohorts",
    )
    max_participants = models.IntegerField(default=30)
    status = models.CharField(max_length=15, choices=CohortStatus.choices, default=CohortStatus.OPEN)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    chat_room_url = models.URLField(blank=True, default="")
    community_url = models.URLField(blank=True, default="")
    application_deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_cohort_program"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.course.title} — {self.name}"


class CohortEnrollment(models.Model):
    """Participant's enrollment in a cohort program."""

    class EnrollmentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        WITHDRAWN = "withdrawn", "Withdrawn"
        WAITLISTED = "waitlisted", "Waitlisted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cohort = models.ForeignKey(CohortProgram, on_delete=models.CASCADE, related_name="enrollments")
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cohort_enrollments",
    )
    status = models.CharField(max_length=15, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE)
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_cohort_enrollment"
        unique_together = [["cohort", "participant"]]

    def __str__(self):
        return f"{self.participant.email} @ {self.cohort}"


class CourseLearningPath(models.Model):
    """Curated sequence of courses forming a learning pathway."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True, default="")
    target_role = models.CharField(max_length=200, blank=True, default="")
    courses = models.ManyToManyField(Course, through="LearningPathCourse", related_name="learning_paths")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_course_learning_path"
        ordering = ["name"]

    def __str__(self):
        return self.name


class LearningPathCourse(models.Model):
    """Through model: maintains ordering of courses within a learning path."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(CourseLearningPath, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "mp_learning_path_course"
        ordering = ["sort_order"]
        unique_together = [["learning_path", "course"]]
