"""
Referrals & Employee Advocacy — Feature 4

Covers:
  - Employee referral portal + referral links + tracked shares
  - Referral campaign pages (role-specific, time-boxed)
  - Referral request workflow (HM prompts referral asks)
  - Bonus program rules + approval and payout tracking
  - Referrer status visibility
  - Referral leaderboards (weekly/monthly/quarterly/all-time)
  - Alumni referral program
  - External ambassador/referrer program
  - Hiring-manager referral prompts
  - Role-specific referral campaigns
  - Referral quality analytics
  - Referral-to-hire conversion tracking
  - Duplicate referral conflict handling
"""

import uuid
from django.db import models


# ── 1. Referral Program ───────────────────────────────────────────────────────

class ReferralProgram(models.Model):
    """A named referral program configuration for a tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="referral_programs")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    allow_alumni = models.BooleanField(default=False, help_text="Allow former employees to refer")
    allow_external = models.BooleanField(default=False, help_text="Allow non-employees / ambassadors to refer")
    bonus_currency = models.CharField(max_length=3, default="USD")
    terms_url = models.URLField(blank=True, default="")
    portal_headline = models.CharField(max_length=255, blank=True, default="")
    portal_description = models.TextField(blank=True, default="")
    portal_banner_url = models.URLField(blank=True, default="")
    # Referral request workflow settings
    enable_hm_prompts = models.BooleanField(default=True, help_text="Prompt HMs to request referrals for open roles")
    hm_prompt_days_after_open = models.PositiveSmallIntegerField(default=7, help_text="Days after job opens to send HM prompt")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "referral_programs"

    def __str__(self):
        return f"{self.name} ({self.tenant})"


# ── 2. Referral Campaign ──────────────────────────────────────────────────────

class ReferralCampaign(models.Model):
    """A time-boxed referral drive for specific roles."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("ended", "Ended"),
        ("paused", "Paused"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="referral_campaigns")
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    target_jobs = models.JSONField(default=list, blank=True, help_text="List of Job UUIDs for this campaign")
    bonus_multiplier = models.FloatField(default=1.0, help_text="Multiplier on top of base BonusRule")
    # Campaign page content
    page_headline = models.CharField(max_length=255, blank=True, default="")
    page_body = models.TextField(blank=True, default="")
    page_image_url = models.URLField(blank=True, default="")
    share_message_template = models.TextField(blank=True, default="")  # merge-tag template for sharing
    # Audience
    target_audience = models.CharField(
        max_length=20,
        choices=[("all", "All Employees"), ("alumni", "Alumni"), ("ambassadors", "External Ambassadors"), ("custom", "Custom")],
        default="all",
    )
    custom_audience_ids = models.JSONField(default=list, blank=True)  # list of user IDs
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "referral_campaigns"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} ({self.status})"


# ── 3. Referral ───────────────────────────────────────────────────────────────

class Referral(models.Model):
    """A single candidate referral record."""

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("screening", "In Screening"),
        ("interviewing", "Interviewing"),
        ("offer_extended", "Offer Extended"),
        ("hired", "Hired"),
        ("not_hired", "Not Hired / Declined"),
        ("pending_payout", "Pending Payout"),
        ("paid", "Paid"),
        ("duplicate", "Duplicate — Conflict"),
        ("withdrawn", "Withdrawn"),
    ]

    REFERRER_TYPE_CHOICES = [
        ("employee", "Current Employee"),
        ("alumni", "Alumni"),
        ("ambassador", "External Ambassador"),
        ("hiring_manager", "Hiring Manager"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="referrals")
    program = models.ForeignKey(ReferralProgram, on_delete=models.PROTECT, related_name="referrals")
    campaign = models.ForeignKey(
        ReferralCampaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals"
    )

    # Referrer info
    referrer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="made_referrals"
    )
    referrer_type = models.CharField(max_length=20, choices=REFERRER_TYPE_CHOICES, default="employee")
    referrer_email = models.EmailField(blank=True, default="", help_text="For alumni / external referrers")
    referrer_name = models.CharField(max_length=255, blank=True, default="")
    referral_link = models.ForeignKey(
        "ReferralLink", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals"
    )

    # Referred candidate
    candidate_email = models.EmailField()
    candidate_name = models.CharField(max_length=255)
    candidate_phone = models.CharField(max_length=30, blank=True, default="")
    candidate_linkedin = models.URLField(blank=True, default="")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals"
    )
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals"
    )

    # Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    referral_note = models.TextField(blank=True, default="")
    relationship = models.CharField(max_length=255, blank=True, default="", help_text="How do they know the candidate?")
    quality_score = models.FloatField(null=True, blank=True, help_text="0-100 referral quality score")

    # Duplicate handling
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="duplicate_referrals"
    )
    duplicate_resolved_at = models.DateTimeField(null=True, blank=True)
    duplicate_resolution_notes = models.TextField(blank=True, default="")

    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    hired_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "referrals"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "referrer"]),
            models.Index(fields=["candidate_email"]),
        ]

    def __str__(self):
        return f"Referral: {self.candidate_name} by {self.referrer_name or self.referrer_email}"


# ── 4. Referral Link ──────────────────────────────────────────────────────────

class ReferralLink(models.Model):
    """Trackable share link for a referral program or specific job."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="referral_links")
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="links")
    referrer = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="referral_links")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="referral_links"
    )
    campaign = models.ForeignKey(
        ReferralCampaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="links"
    )
    token = models.CharField(max_length=64, unique=True)
    utm_source = models.CharField(max_length=100, blank=True, default="")
    utm_medium = models.CharField(max_length=100, blank=True, default="")
    click_count = models.IntegerField(default=0)
    conversion_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "referral_links"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Link by {self.referrer} — {self.click_count} clicks"


# ── 5. Bonus Rule ─────────────────────────────────────────────────────────────

class BonusRule(models.Model):
    """Bonus payout rule for a referral program."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="bonus_rules")
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="bonus_rules")
    name = models.CharField(max_length=255)
    trigger_event = models.CharField(
        max_length=50, default="hired",
        help_text="e.g. hired, passed_day_90, passed_probation, offer_extended"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    department_filter = models.CharField(max_length=150, blank=True, default="")
    job_level_filter = models.CharField(max_length=100, blank=True, default="")
    referrer_type_filter = models.CharField(max_length=20, blank=True, default="", help_text="Limit to employee/alumni/ambassador")
    requires_approval = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bonus_rules"

    def __str__(self):
        return f"{self.name}: {self.currency} {self.amount} on {self.trigger_event}"


# ── 6. Bonus Payout ───────────────────────────────────────────────────────────

class BonusPayout(models.Model):
    """Individual bonus payout record."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
        ("on_hold", "On Hold"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="bonus_payouts")
    referral = models.ForeignKey(Referral, on_delete=models.PROTECT, related_name="payouts")
    rule = models.ForeignKey(BonusRule, on_delete=models.SET_NULL, null=True, related_name="payouts")
    recipient = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="bonus_payouts"
    )
    recipient_email = models.EmailField(blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_payouts"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bonus_payouts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payout {self.amount} {self.currency} — {self.status}"


# ── 7. Referral Leaderboard ───────────────────────────────────────────────────

class ReferralLeaderboard(models.Model):
    """Cached leaderboard snapshot for a program and period."""

    PERIOD_CHOICES = [
        ("week", "Weekly"),
        ("month", "Monthly"),
        ("quarter", "Quarterly"),
        ("all_time", "All Time"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="referral_leaderboards")
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="leaderboards")
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default="month")
    period_start = models.DateField()
    rankings = models.JSONField(
        default=list,
        help_text="[{'user_id':..., 'name':..., 'referrals':5, 'hires':2, 'earnings':500}]"
    )
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "referral_leaderboards"
        ordering = ["-period_start"]

    def __str__(self):
        return f"Leaderboard {self.period} starting {self.period_start}"


# ── 8. Referral Request ───────────────────────────────────────────────────────

class ReferralRequest(models.Model):
    """
    A request from a recruiter or hiring manager asking employees to refer
    candidates for a specific job. Powers the HM referral prompt workflow.
    """

    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("viewed", "Viewed"),
        ("acted", "Acted — Referral Submitted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="referral_requests")
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="requests")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, related_name="referral_requests"
    )
    campaign = models.ForeignKey(
        ReferralCampaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests"
    )
    # Who's being asked to refer
    requested_from = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="referral_requests_received"
    )
    # Who sent the request (recruiter or HM)
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="referral_requests_sent"
    )
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    is_hm_prompt = models.BooleanField(default=False, help_text="Auto-generated from HM prompt rule")
    sent_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "referral_requests"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Request: {self.requested_by} → {self.requested_from} for {self.job}"


# ── 9. Ambassador Profile ─────────────────────────────────────────────────────

class AmbassadorProfile(models.Model):
    """
    External ambassador or alumni referrer profile.
    Allows non-employees to participate in referral programs.
    """

    TYPE_CHOICES = [
        ("alumni", "Alumni"),
        ("external_ambassador", "External Ambassador"),
        ("contractor", "Contractor"),
        ("partner", "Partner / Vendor"),
    ]

    STATUS_CHOICES = [
        ("invited", "Invited"),
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("revoked", "Revoked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="ambassador_profiles")
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="ambassadors")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ambassador_profiles"
    )
    # For non-users
    name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    company = models.CharField(max_length=255, blank=True, default="")
    ambassador_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="external_ambassador")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="invited")
    invite_token = models.CharField(max_length=64, unique=True, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    total_referrals = models.PositiveIntegerField(default=0)
    total_hires = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")
    invited_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invited_ambassadors"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "referral_ambassador_profiles"
        ordering = ["-total_hires", "-total_referrals"]

    def __str__(self):
        return f"Ambassador: {self.name or self.email} ({self.ambassador_type})"


# ── 10. HM Referral Prompt ────────────────────────────────────────────────────

class HMReferralPrompt(models.Model):
    """
    Hiring manager referral prompt record — auto-generated when a job opens
    and the program has enable_hm_prompts=True.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Send"),
        ("sent", "Sent"),
        ("viewed", "Viewed"),
        ("referrals_submitted", "Referrals Submitted"),
        ("no_action", "No Action Taken"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="hm_prompts")
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name="hm_prompts")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="hm_prompts")
    hiring_manager = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="hm_referral_prompts"
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    referrals_submitted_count = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "referral_hm_prompts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"HM Prompt: {self.hiring_manager} for {self.job} ({self.status})"


# ── 11. Referral Quality Score ────────────────────────────────────────────────

class ReferralQualityScore(models.Model):
    """
    Detailed quality scoring breakdown for a referral.
    Powers referral quality analytics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referral = models.OneToOneField(Referral, on_delete=models.CASCADE, related_name="quality_detail")
    # Score components (0-100 each)
    profile_completeness = models.FloatField(default=0.0)   # Did referrer fill out the form?
    skills_match = models.FloatField(default=0.0)           # How well do skills match job?
    relationship_strength = models.FloatField(default=0.0)  # How strong is the personal connection?
    interview_pass_rate = models.FloatField(default=0.0)    # Historical: this referrer's pass rate
    time_to_hire = models.FloatField(default=0.0)           # Speed relative to avg pipeline
    overall_score = models.FloatField(default=0.0)          # Weighted composite
    scored_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "referral_quality_scores"

    def __str__(self):
        return f"Quality {self.overall_score:.1f} for {self.referral}"


# ── 12. Referral Analytics Snapshot ──────────────────────────────────────────

class ReferralAnalyticsSnapshot(models.Model):
    """
    Daily/monthly snapshot of referral funnel metrics for a program.
    Powers referral-to-hire conversion and ROI analytics.
    """

    PERIOD_CHOICES = [
        ("day", "Daily"),
        ("week", "Weekly"),
        ("month", "Monthly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="referral_snapshots")
    program = models.ForeignKey(
        ReferralProgram, on_delete=models.CASCADE, related_name="analytics_snapshots"
    )
    snapshot_date = models.DateField()
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="day")

    # Funnel counts
    total_referrals = models.PositiveIntegerField(default=0)
    under_review = models.PositiveIntegerField(default=0)
    screening = models.PositiveIntegerField(default=0)
    interviewing = models.PositiveIntegerField(default=0)
    offers = models.PositiveIntegerField(default=0)
    hired = models.PositiveIntegerField(default=0)
    not_hired = models.PositiveIntegerField(default=0)
    duplicates = models.PositiveIntegerField(default=0)

    # Quality
    avg_quality_score = models.FloatField(default=0.0)
    avg_time_to_hire_days = models.FloatField(null=True, blank=True)

    # Bonus / ROI
    total_bonus_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_bonus_pending = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_per_hire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # By referrer type
    employee_referrals = models.PositiveIntegerField(default=0)
    alumni_referrals = models.PositiveIntegerField(default=0)
    ambassador_referrals = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "referral_analytics_snapshots"
        ordering = ["-snapshot_date"]
        unique_together = [("tenant", "program", "snapshot_date", "period")]

    def __str__(self):
        return f"Snapshot {self.snapshot_date} — {self.program}"
