"""Candidates app — Seeker profiles, resumes, skills, experience, education.
Features from Plan Part 2 (#201–450).
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator


class SeekerProfile(models.Model):
    """Job seeker profile — covers #201-245."""

    class SearchStatus(models.TextChoices):
        ACTIVELY_LOOKING = "actively_looking", "Actively Looking"
        OPEN_TO_OFFERS = "open_to_offers", "Open to Offers"
        NOT_LOOKING = "not_looking", "Not Looking"
        EMPLOYED_LOOKING = "employed_looking", "Employed, Looking"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        HIDDEN = "hidden", "Hidden"
        ANONYMOUS = "anonymous", "Anonymous"

    class HighestEducation(models.TextChoices):
        BELOW_OL = "below_ol", "Below O/L"
        OL_PASSED = "ol_passed", "O/L Passed"
        AL_PASSED = "al_passed", "A/L Passed"
        DIPLOMA = "diploma", "Diploma"
        NVQ = "nvq", "NVQ"
        BACHELORS = "bachelors", "Bachelor's Degree"
        MASTERS = "masters", "Master's Degree"
        PHD = "phd", "PhD / Doctorate"
        PROFESSIONAL = "professional", "Professional Qualification"

    class WizardStep(models.IntegerChoices):
        PERSONAL = 1, "Personal"
        EDUCATION = 2, "Education"
        EXPERIENCE = 3, "Experience"
        SKILLS = 4, "Skills"
        PREFERENCES = 5, "Preferences"
        COMPLETED = 6, "Completed"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seeker_profile")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    first_name_si = models.CharField(max_length=100, blank=True, default="")
    first_name_ta = models.CharField(max_length=100, blank=True, default="")
    last_name_si = models.CharField(max_length=100, blank=True, default="")
    last_name_ta = models.CharField(max_length=100, blank=True, default="")
    headline = models.CharField(max_length=200, blank=True, default="")
    headline_si = models.CharField(max_length=200, blank=True, default="")
    headline_ta = models.CharField(max_length=200, blank=True, default="")
    bio = models.TextField(blank=True, default="", help_text="Max 500 words")  # #210
    bio_si = models.TextField(blank=True, default="")
    bio_ta = models.TextField(blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other"), ("prefer_not_to_say", "Prefer not to say")],
        blank=True, default="",
    )
    nic_number = models.CharField(max_length=12, null=True, blank=True)
    phone_secondary = models.CharField(max_length=15, blank=True, default="")  # #211
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField(blank=True, default="")

    # Photo #207
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", null=True, blank=True)

    # Contact preferences #211
    show_email = models.BooleanField(default=True)
    show_phone = models.BooleanField(default=True)
    preferred_contact = models.CharField(
        max_length=10,
        choices=[("email", "Email"), ("phone", "Phone"), ("whatsapp", "WhatsApp")],
        default="email",
    )

    # Social links #237
    linkedin_url = models.URLField(max_length=300, blank=True, default="")
    github_url = models.URLField(max_length=300, blank=True, default="")
    portfolio_url = models.URLField(max_length=300, blank=True, default="")
    website_url = models.URLField(max_length=300, blank=True, default="")

    # Video intro #238
    video_intro_url = models.URLField(max_length=500, blank=True, default="")

    # Driving license #240
    driving_license = models.JSONField(default=list, blank=True, help_text="SL license categories e.g. ['A','B1','C']")

    # Education
    highest_education = models.CharField(max_length=20, choices=HighestEducation.choices, blank=True, default="")
    ol_results = models.JSONField(null=True, blank=True)  # #213
    al_results = models.JSONField(null=True, blank=True)  # #214
    al_stream = models.CharField(max_length=20, blank=True, default="", choices=[
        ("science", "Science"), ("commerce", "Commerce"), ("arts", "Arts"), ("technology", "Technology"),
    ])
    al_zscore = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    university = models.CharField(max_length=200, null=True, blank=True)
    degree_title = models.CharField(max_length=200, null=True, blank=True)

    # Preferences #229
    desired_job_types = models.JSONField(default=list, blank=True)
    desired_industries = models.JSONField(default=list, blank=True)
    desired_locations = models.JSONField(default=list, blank=True)
    min_salary_expected = models.IntegerField(null=True, blank=True)  # #233
    max_salary_expected = models.IntegerField(null=True, blank=True)
    willing_to_relocate = models.BooleanField(default=False)  # #232
    relocation_districts = models.JSONField(default=list, blank=True)
    open_to_remote = models.BooleanField(default=False)
    available_from = models.DateField(null=True, blank=True)  # #231

    # Status
    job_search_status = models.CharField(max_length=20, choices=SearchStatus.choices, default=SearchStatus.ACTIVELY_LOOKING)  # #230
    profile_visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)  # #234
    blocked_companies = models.ManyToManyField("employers.EmployerAccount", blank=True, related_name="blocked_by_seekers")  # #235
    profile_completeness = models.IntegerField(default=0)  # #204
    last_active_at = models.DateTimeField(auto_now=True)

    # Wizard #201-203
    wizard_step = models.IntegerField(choices=WizardStep.choices, default=WizardStep.PERSONAL)
    wizard_completed = models.BooleanField(default=False)

    # Profile edit history #243
    last_profile_edit = models.DateTimeField(null=True, blank=True)

    # ATS link
    ats_candidate_id = models.UUIDField(null=True, blank=True, unique=True)

    # ── Marketplace Enhancements ──
    public_profile_slug = models.SlugField(max_length=150, blank=True, default="", unique=True,
                                           help_text="Slug for public profile URL")
    open_to_work = models.BooleanField(default=False, help_text="Show 'Open to Work' badge publicly")
    recruiter_visibility = models.CharField(
        max_length=15,
        choices=[("all", "All Recruiters"), ("premium_only", "Premium Recruiters Only"), ("none", "Hidden")],
        default="all",
        help_text="Who can see seeker in recruiter search",
    )
    trust_score = models.IntegerField(default=50, help_text="0–100 seeker trust score")
    commute_radius_km = models.IntegerField(default=25, help_text="Maximum commute radius in km")
    notice_period_weeks = models.IntegerField(null=True, blank=True, help_text="Current notice period in weeks")
    preferred_shift = models.CharField(
        max_length=15,
        choices=[("day", "Day Shift"), ("night", "Night Shift"), ("rotating", "Rotating"), ("flexible", "Flexible")],
        blank=True, default="",
    )
    work_auth = models.CharField(
        max_length=20,
        choices=[
            ("citizen", "Citizen"), ("permanent_resident", "Permanent Resident"),
            ("work_permit", "Work Permit"), ("student_visa", "Student Visa"),
        ],
        blank=True, default="",
        help_text="Work authorization status",
    )
    last_job_alert_match = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_seeker_profiles"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def compute_completeness(self):
        """Calculate profile completeness percentage. #204"""
        weights = {
            "first_name": 5, "last_name": 5, "headline": 5, "bio": 5,
            "date_of_birth": 3, "gender": 2, "nic_number": 3,
            "district": 3, "city": 2, "avatar": 5,
            "highest_education": 5, "ol_results": 3, "al_results": 3,
            "desired_job_types": 3, "desired_locations": 3,
            "linkedin_url": 2, "min_salary_expected": 2,
        }
        score = 0
        for field, weight in weights.items():
            val = getattr(self, field, None)
            if val and val not in ("", [], None, {}):
                score += weight
        # Related objects
        if self.resumes.filter(is_primary=True).exists():
            score += 15
        if self.skills.exists():
            score += 10
        if self.experiences.exists():
            score += 10
        if self.education.exists():
            score += 5
        self.profile_completeness = min(score, 100)
        return self.profile_completeness

    def get_suggestions(self):
        """Return suggestions for improving profile completeness. #204"""
        suggestions = []
        if not self.avatar:
            suggestions.append("Add a profile photo to reach higher visibility")
        if not self.headline:
            suggestions.append("Add a headline to stand out")
        if not self.bio:
            suggestions.append("Write a short bio")
        if not self.ol_results:
            suggestions.append("Add your O/L results")
        if not self.skills.exists():
            suggestions.append("Add at least 3 skills")
        if not self.experiences.exists():
            suggestions.append("Add your work experience")
        if not self.resumes.filter(is_primary=True).exists():
            suggestions.append("Upload and set a primary resume")
        if not self.linkedin_url:
            suggestions.append("Add your LinkedIn profile")
        return suggestions


class SeekerReference(models.Model):
    """Professional references. #241"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="references")
    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    relationship = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "jf_seeker_references"


class SeekerPortfolio(models.Model):
    """Portfolio / work samples. #239"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="portfolio_items")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    url = models.URLField(max_length=500, blank=True, default="")
    file = models.FileField(upload_to="portfolio/%Y/%m/", null=True, blank=True)
    file_type = models.CharField(max_length=10, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_seeker_portfolio"
        ordering = ["sort_order"]


class SkillEndorsement(models.Model):
    """Skill endorsements by other users. #226"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker_skill = models.ForeignKey("SeekerSkill", on_delete=models.CASCADE, related_name="endorsements")
    endorsed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_skill_endorsements"
        unique_together = ["seeker_skill", "endorsed_by"]


class SeekerResume(models.Model):
    """Uploaded resumes. #246-280"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=100, default="My Resume")  # #249
    file = models.FileField(
        upload_to="resumes/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
    )
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file_type = models.CharField(max_length=10, choices=[("pdf", "PDF"), ("doc", "DOC"), ("docx", "DOCX")])
    file_size_bytes = models.IntegerField(default=0)
    raw_text = models.TextField(blank=True, default="")  # #252 extracted text
    parsed_json = models.JSONField(null=True, blank=True)  # #252 AI-parsed structure
    parse_status = models.CharField(
        max_length=15,
        choices=[("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")],
        default="pending",
    )  # #253
    detected_language = models.CharField(max_length=5, blank=True, default="")  # #277
    quality_score = models.IntegerField(null=True, blank=True)  # #256
    quality_tips = models.JSONField(default=list, blank=True)  # #257
    is_primary = models.BooleanField(default=False)  # #248
    is_confidential = models.BooleanField(default=False)  # #258
    privacy = models.CharField(  # #272
        max_length=15,
        choices=[("all", "Show to all"), ("saved_jobs", "Saved jobs only"), ("hidden", "Hidden")],
        default="all",
    )
    include_photo = models.BooleanField(default=False)  # #276
    version_number = models.IntegerField(default=1)  # #266
    virus_scanned = models.BooleanField(default=False)  # #268
    virus_clean = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)  # #273
    uploaded_at = models.DateTimeField(auto_now_add=True)
    refreshed_at = models.DateTimeField(null=True, blank=True)  # #275

    class Meta:
        db_table = "jf_seeker_resumes"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.seeker} — {self.title}"


class SeekerSkill(models.Model):
    """Skills with proficiency levels."""
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="skills")
    skill = models.ForeignKey("taxonomy.Skill", on_delete=models.CASCADE)
    proficiency = models.CharField(
        max_length=15,
        choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced"), ("expert", "Expert")],
        default="intermediate",
    )
    years_used = models.IntegerField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    endorsed_count = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_seeker_skills"
        unique_together = ["seeker", "skill"]


class SeekerExperience(models.Model):
    """Work experience entries. #219-222"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="experiences")
    company_name = models.CharField(max_length=200)
    company_link = models.ForeignKey(
        "employers.EmployerAccount", on_delete=models.SET_NULL, null=True, blank=True
    )  # #221
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    employment_type = models.CharField(
        max_length=15,
        choices=[
            ("full_time", "Full Time"), ("part_time", "Part Time"), ("contract", "Contract"),
            ("internship", "Internship"), ("freelance", "Freelance"),
        ],
        default="full_time",
    )
    gap_explanation = models.TextField(blank=True, default="")  # #222
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_seeker_experiences"
        ordering = ["-start_date"]


class SeekerEducation(models.Model):
    """Education history. #213-218"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=200)
    level = models.CharField(
        max_length=20,
        choices=[
            ("ol", "O/L"), ("al", "A/L"), ("diploma", "Diploma"),
            ("nvq_3", "NVQ 3"), ("nvq_4", "NVQ 4"), ("nvq_5", "NVQ 5"), ("nvq_6", "NVQ 6"), ("nvq_7", "NVQ 7"),
            ("hnd", "HND"), ("bachelors", "Bachelor's"), ("postgrad_diploma", "Postgrad Diploma"),
            ("masters", "Master's"), ("phd", "PhD"), ("professional_cert", "Professional Certificate"),
        ],
    )
    field_of_study = models.CharField(max_length=200, blank=True, default="")
    degree_class = models.CharField(max_length=50, blank=True, default="")  # #215 First Class, Second Upper, etc.
    grade = models.CharField(max_length=50, blank=True, default="")
    start_year = models.IntegerField()
    end_year = models.IntegerField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_seeker_education"
        ordering = ["-start_year"]


class SeekerCertification(models.Model):
    """Professional certifications."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=200)
    issuing_org = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=100, blank=True, default="")
    credential_url = models.URLField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "jf_seeker_certifications"
        ordering = ["-issue_date"]


class SeekerLanguage(models.Model):
    """Language proficiencies."""
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="languages")
    language = models.CharField(max_length=50)
    proficiency = models.CharField(
        max_length=15,
        choices=[("basic", "Basic"), ("conversational", "Conversational"), ("professional", "Professional"), ("native", "Native")],
    )

    class Meta:
        db_table = "jf_seeker_languages"
        unique_together = ["seeker", "language"]


# ── Career Roadmap ────────────────────────────────────────────────────────────

class CareerRoadmap(models.Model):
    """Target role planning with milestones and timeline."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ACHIEVED = "achieved", "Achieved"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="roadmaps")
    target_role = models.CharField(max_length=200)
    target_industry = models.CharField(max_length=200, blank=True, default="")
    current_readiness = models.IntegerField(default=0, help_text="0-100 readiness score")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    target_date = models.DateField(null=True, blank=True)
    milestones = models.JSONField(default=list, blank=True, help_text="List of milestone objects with title, done, due_date")
    skill_gaps = models.JSONField(default=list, blank=True)
    recommended_actions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_career_roadmaps"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.seeker} → {self.target_role}"


# ── Mock Interviews ───────────────────────────────────────────────────────────

class MockInterview(models.Model):
    """AI or human mock interview session with structured feedback."""

    class InterviewMode(models.TextChoices):
        AI = "ai", "AI-Powered"
        HUMAN = "human", "Human Expert"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="mock_interviews")
    mode = models.CharField(max_length=10, choices=InterviewMode.choices, default=InterviewMode.AI)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    target_role = models.CharField(max_length=200, blank=True, default="")
    interview_type = models.CharField(
        max_length=20, default="behavioral",
        choices=[("behavioral", "Behavioral"), ("technical", "Technical"), ("case", "Case Study"), ("culture", "Culture Fit")]
    )
    duration_minutes = models.IntegerField(default=30)
    questions = models.JSONField(default=list, blank=True)
    responses = models.JSONField(default=list, blank=True)
    feedback = models.JSONField(default=dict, blank=True)
    overall_score = models.IntegerField(null=True, blank=True, help_text="0-100")
    strengths = models.JSONField(default=list, blank=True)
    improvements = models.JSONField(default=list, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_mock_interviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Mock Interview: {self.seeker} ({self.get_mode_display()})"


# ── Seeker Badges ─────────────────────────────────────────────────────────────

class SeekerBadge(models.Model):
    """Profile achievement badges awarded to seekers. #204 milestones."""

    class BadgeType(models.TextChoices):
        PROFILE_COMPLETE = "profile_complete", "Profile Complete"
        RESUME_UPLOADED = "resume_uploaded", "Resume Uploaded"
        SKILL_VERIFIED = "skill_verified", "Skill Verified"
        TEN_APPLICATIONS = "10_applications", "10 Applications"
        FIRST_APPLY = "first_apply", "First Application"
        OPEN_TO_WORK = "open_to_work", "Open To Work"
        CAREEROS_IMPORT = "careeros_import", "CareerOS Import"
        TOP_APPLICANT = "top_applicant", "Top Applicant"
        TRUSTED = "trusted", "Trusted Profile"
        MULTILINGUAL = "multilingual", "Multilingual"
        LINKEDIN_CONNECTED = "linkedin_connected", "LinkedIn Connected"
        CERTIFIED = "certified", "Certified Professional"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="badges")
    badge_type = models.CharField(max_length=30, choices=BadgeType.choices)
    awarded_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "jf_seeker_badges"
        unique_together = [["seeker", "badge_type"]]
        ordering = ["awarded_at"]

    def __str__(self):
        return f"{self.seeker} — {self.get_badge_type_display()}"


# ── Activity Timeline ─────────────────────────────────────────────────────────

class SeekerActivityTimeline(models.Model):
    """Records seeker activity events for the profile activity timeline."""

    class EventType(models.TextChoices):
        PROFILE_UPDATED = "profile_updated", "Profile Updated"
        RESUME_UPLOADED = "resume_uploaded", "Resume Uploaded"
        APPLICATION_SENT = "application_sent", "Application Sent"
        JOB_SAVED = "job_saved", "Job Saved"
        JOB_VIEWED = "job_viewed", "Job Viewed"
        BADGE_EARNED = "badge_earned", "Badge Earned"
        SEARCH_DONE = "search_done", "Search Performed"
        PREFERENCES_UPDATED = "preferences_updated", "Preferences Updated"
        VISIBILITY_CHANGED = "visibility_changed", "Visibility Changed"
        CAREEROS_IMPORT = "careeros_import", "CareerOS Profile Import"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
        OFFER_RECEIVED = "offer_received", "Offer Received"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="timeline_events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True, help_text="Extra event-specific data")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_seeker_timeline"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["seeker", "-created_at"], name="idx_timeline_seeker")
        ]

    def __str__(self):
        return f"{self.seeker} — {self.get_event_type_display()} at {self.created_at:%Y-%m-%d}"


# ── Reusable Application Profile ──────────────────────────────────────────────

class ApplicationProfile(models.Model):
    """
    One-click / auto-fill application profile.
    Stores pre-filled answers to common employer questions so seekers can
    apply to jobs without re-entering the same information every time.
    """
    seeker = models.OneToOneField(SeekerProfile, on_delete=models.CASCADE, related_name="application_profile")
    full_name_override = models.CharField(max_length=200, blank=True, default="")
    phone_override = models.CharField(max_length=20, blank=True, default="")
    email_override = models.EmailField(blank=True, default="")
    cover_letter_template = models.TextField(blank=True, default="", help_text="Default cover letter template, use {{job_title}} / {{company_name}} placeholders")
    expected_salary = models.IntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=5, default="LKR")
    work_auth_statement = models.CharField(max_length=300, blank=True, default="")
    linkedin_url = models.URLField(max_length=300, blank=True, default="")
    portfolio_url = models.URLField(max_length=300, blank=True, default="")
    github_url = models.URLField(max_length=300, blank=True, default="")
    additional_questions = models.JSONField(
        default=dict, blank=True,
        help_text="Pre-filled answers to common employer questions keyed by question text"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_application_profiles"

    def __str__(self):
        return f"Application profile: {self.seeker}"

