"""Employers app — Company accounts, team, branding.
Defined in Part 1 schema §5.2.
"""
import uuid
from django.db import models
from django.conf import settings


class EmployerAccount(models.Model):
    """Company/employer profile."""

    class Plan(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        PROFESSIONAL = "professional", "Professional"
        ENTERPRISE = "enterprise", "Enterprise"
        AGENCY = "agency", "Agency"

    class CompanySize(models.TextChoices):
        MICRO = "1-10", "1–10"
        SMALL = "11-50", "11–50"
        MEDIUM = "51-200", "51–200"
        LARGE = "201-500", "201–500"
        XLARGE = "501-1000", "501–1000"
        ENTERPRISE = "1001-5000", "1001–5000"
        MEGA = "5000+", "5000+"

    class VerificationBadge(models.TextChoices):
        NONE = "none", "None"
        BASIC = "basic", "Basic"
        PREMIUM = "premium", "Premium"
        GOVERNMENT = "government", "Government"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=200)
    company_name_si = models.CharField(max_length=200, blank=True, default="")
    company_name_ta = models.CharField(max_length=200, blank=True, default="")
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="company_covers/", null=True, blank=True)
    website = models.URLField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    description_si = models.TextField(blank=True, default="")
    description_ta = models.TextField(blank=True, default="")
    industry = models.ForeignKey("taxonomy.Industry", on_delete=models.SET_NULL, null=True, blank=True)
    company_size = models.CharField(max_length=10, choices=CompanySize.choices, blank=True, default="")
    founded_year = models.IntegerField(null=True, blank=True)
    headquarters = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    registration_no = models.CharField(max_length=50, blank=True, default="")
    tax_id = models.CharField(max_length=50, blank=True, default="")
    is_verified = models.BooleanField(default=False)
    verification_badge = models.CharField(max_length=10, choices=VerificationBadge.choices, default=VerificationBadge.NONE)

    # Social links
    linkedin_url = models.URLField(max_length=500, blank=True, default="")
    facebook_url = models.URLField(max_length=500, blank=True, default="")
    twitter_url = models.URLField(max_length=500, blank=True, default="")
    youtube_url = models.URLField(max_length=500, blank=True, default="")

    # Subscription
    plan = models.CharField(max_length=15, choices=Plan.choices, default=Plan.FREE)
    plan_expires_at = models.DateTimeField(null=True, blank=True)
    monthly_job_limit = models.IntegerField(default=3)
    resume_db_access = models.BooleanField(default=False)
    active_job_count = models.IntegerField(default=0)

    # ATS Connection (#35, Features #451+)
    ats_connected = models.BooleanField(default=False)
    ats_tenant_slug = models.CharField(max_length=100, blank=True, default="")
    ats_api_key_encrypted = models.TextField(blank=True, default="")
    ats_webhook_secret_encrypted = models.TextField(blank=True, default="")
    ats_sync_enabled = models.BooleanField(default=False)
    ats_last_sync_at = models.DateTimeField(null=True, blank=True)

    # Stats
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    follower_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_employer_accounts"

    def __str__(self):
        return self.company_name


class EmployerTeamMember(models.Model):
    """Team members who can manage jobs on behalf of the employer."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        RECRUITER = "recruiter", "Recruiter"
        VIEWER = "viewer", "Viewer"

    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="team_members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employer_memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.RECRUITER)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jf_employer_team_members"
        unique_together = ["employer", "user"]


class EmployerBranding(models.Model):
    """Company branding/culture page customisation."""
    employer = models.OneToOneField(EmployerAccount, on_delete=models.CASCADE, related_name="branding")
    primary_color = models.CharField(max_length=7, default="#2563EB")
    banner_images = models.JSONField(default=list, blank=True)
    employee_testimonials = models.JSONField(default=list, blank=True)
    benefits = models.JSONField(default=list, blank=True)
    office_photos = models.JSONField(default=list, blank=True)
    video_url = models.URLField(max_length=500, blank=True, default="")
    culture_keywords = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "jf_employer_branding"


class EmployerFollow(models.Model):
    """A seeker following a company — #366-368."""
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="follows")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followed_employers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_employer_follows"
        unique_together = ["employer", "user"]

    def __str__(self):
        return f"{self.user} follows {self.employer}"


class SalaryReport(models.Model):
    """Anonymous salary report submitted by employees — #388."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="salary_reports")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    job_title = models.CharField(max_length=150)
    department = models.CharField(max_length=100, blank=True, default="")
    experience_years = models.IntegerField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_comp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, default="LKR")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_salary_reports"
        ordering = ["-created_at"]


# ── JD Builder ────────────────────────────────────────────────────────────────

class JobDescription(models.Model):
    """AI-generated job description."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="job_descriptions")
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True, default="")
    level = models.CharField(max_length=50, blank=True, default="")
    skills = models.JSONField(default=list)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    content = models.TextField()
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_job_descriptions"
        ordering = ["-created_at"]


# ── Interview Kits ────────────────────────────────────────────────────────────

class InterviewKit(models.Model):
    """Structured interview kit."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="interview_kits")
    title = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    scoring_criteria = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_interview_kits"
        ordering = ["-created_at"]


class InterviewQuestion(models.Model):
    """Question in an interview kit."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kit = models.ForeignKey(InterviewKit, on_delete=models.CASCADE, related_name="questions")
    category = models.CharField(max_length=50)  # Behavioral, Technical, etc.
    question = models.TextField()
    expected_answer = models.TextField(blank=True, default="")
    max_score = models.IntegerField(default=5)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_interview_questions"
        ordering = ["sort_order"]


# ── Silver Medalists ──────────────────────────────────────────────────────────

class SilverMedalist(models.Model):
    """Strong past candidate for re-engagement."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="silver_medalists")
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    original_role = models.CharField(max_length=200)
    score = models.IntegerField(default=0)
    skills = models.JSONField(default=list)
    recruiter_notes = models.TextField(blank=True, default="")
    applied_date = models.DateField(null=True, blank=True)
    last_contacted = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="available")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_silver_medalists"
        ordering = ["-score"]


# ── Referral Campaigns ────────────────────────────────────────────────────────

class ReferralCampaign(models.Model):
    """Employee referral campaign."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="referral_campaigns")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    reward_amount = models.IntegerField(default=0)
    reward_currency = models.CharField(max_length=5, default="LKR")
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_referral_campaigns"
        ordering = ["-created_at"]


class Referral(models.Model):
    """Individual referral in a campaign."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(ReferralCampaign, on_delete=models.CASCADE, related_name="referrals")
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="referrals_made")
    candidate_name = models.CharField(max_length=200)
    candidate_email = models.EmailField(blank=True, default="")
    role = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=20, default="submitted")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_referrals"
        ordering = ["-created_at"]


# ── Recruiter CRM ─────────────────────────────────────────────────────────────

class RecruiterContact(models.Model):
    """CRM contact for recruiter pipeline."""

    class Stage(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        ENGAGED = "engaged", "Engaged"
        QUALIFIED = "qualified", "Qualified"
        PIPELINE = "pipeline", "Pipeline"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="crm_contacts")
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    role_interest = models.CharField(max_length=200, blank=True, default="")
    source = models.CharField(max_length=100, blank=True, default="")
    stage = models.CharField(max_length=15, choices=Stage.choices, default=Stage.NEW)
    skills = models.JSONField(default=list)
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    last_contact = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_recruiter_contacts"
        ordering = ["-score"]


# ── Career Site CMS ───────────────────────────────────────────────────────────

class CareerSitePage(models.Model):
    """Employer career site page configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.OneToOneField(EmployerAccount, on_delete=models.CASCADE, related_name="career_site")
    company_name = models.CharField(max_length=200)
    primary_color = models.CharField(max_length=10, default="#2563eb")
    sections = models.JSONField(default=list)
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_career_site_pages"


# ── Interview Debriefs ────────────────────────────────────────────────────────

class InterviewDebrief(models.Model):
    """Post-interview debrief session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="debriefs")
    candidate_name = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    date = models.DateField()
    consensus = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_interview_debriefs"
        ordering = ["-date"]


class DebriefFeedback(models.Model):
    """Individual interviewer feedback in a debrief."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    debrief = models.ForeignKey(InterviewDebrief, on_delete=models.CASCADE, related_name="feedback")
    interviewer_name = models.CharField(max_length=200)
    interviewer_role = models.CharField(max_length=200, blank=True, default="")
    score = models.IntegerField(default=0)
    recommendation = models.CharField(max_length=50, default="Pending")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "jf_debrief_feedback"


# ── Talent Pools ──────────────────────────────────────────────────────────────

class TalentPool(models.Model):
    """Named candidate pool for re-engagement (silver medalists, passive, etc.)."""

    class PoolType(models.TextChoices):
        SILVER_MEDALIST = "silver_medalist", "Silver Medalists"
        PASSIVE = "passive", "Passive Candidates"
        REFERRAL = "referral", "Referral Pool"
        DIVERSITY = "diversity", "Diversity Pipeline"
        ALUMNI = "alumni", "Alumni"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="talent_pools")
    name = models.CharField(max_length=200)
    pool_type = models.CharField(max_length=20, choices=PoolType.choices, default=PoolType.CUSTOM)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    member_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_talent_pools"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.member_count})"


class TalentPoolMember(models.Model):
    """Candidate membership in a talent pool."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(TalentPool, on_delete=models.CASCADE, related_name="members")
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="talent_pool_memberships"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="talent_pool_additions"
    )
    source = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    last_contacted = models.DateTimeField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_talent_pool_members"
        unique_together = ["pool", "candidate"]
        ordering = ["-added_at"]


# ── Nurture Campaigns ─────────────────────────────────────────────────────────

class NurtureCampaign(models.Model):
    """Email/SMS drip campaign for talent pool engagement."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerAccount, on_delete=models.CASCADE, related_name="nurture_campaigns")
    pool = models.ForeignKey(TalentPool, on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns")
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    subject = models.CharField(max_length=300, blank=True, default="")
    content = models.TextField(blank=True, default="")
    target_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    reply_count = models.IntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_nurture_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
