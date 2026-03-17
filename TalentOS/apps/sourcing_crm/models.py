"""
Sourcing CRM & Talent Pools — Feature 3

Covers:
  - Sourced prospects (separate from applicants)
  - Talent pools (skill/geo/seniority/clearance/license/source/type)
  - Pool membership with engagement scoring
  - Recruiter ownership + follow-up tasks + cadences
  - Nurture sequences + sequence enrollment
  - Outreach messages (email/SMS/WhatsApp)
  - Outreach campaigns + campaign steps
  - Saved segments
  - Do-not-contact / suppression lists
  - Consent-aware sourcing + preference center
  - Warm intro tracking + referral relationship graph
  - Pool health snapshots
  - Lead-to-applicant conversion tracking
  - Outreach performance analytics
"""

import uuid
from django.db import models


# ── 1. Prospect ───────────────────────────────────────────────────────────────

class Prospect(models.Model):
    """
    A sourced individual who has NOT yet applied.
    Sits upstream of the Candidate/Application pipeline.
    """

    STAGE_CHOICES = [
        ("identified", "Identified"),
        ("contacted", "Contacted"),
        ("engaged", "Engaged"),
        ("nurturing", "Nurturing"),
        ("ready", "Ready to Re-engage"),
        ("converted", "Converted to Applicant"),
        ("archived", "Archived"),
        ("do_not_contact", "Do Not Contact"),
    ]

    SOURCE_CHOICES = [
        ("linkedin", "LinkedIn"),
        ("github", "GitHub"),
        ("twitter", "Twitter/X"),
        ("referral", "Referral"),
        ("event", "Event / Conference"),
        ("campus", "Campus Recruiting"),
        ("alumni", "Alumni"),
        ("silver_medalist", "Silver Medalist"),
        ("contractor", "Contractor / Freelancer"),
        ("talent_community", "Talent Community"),
        ("inbound", "Inbound Interest"),
        ("job_board", "Job Board"),
        ("agency", "Agency / Vendor"),
        ("other", "Other"),
    ]

    CONSENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("granted", "Granted"),
        ("withdrawn", "Withdrawn"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sourcing_prospects")

    # Identity
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")
    twitter_url = models.URLField(blank=True, default="")
    personal_site = models.URLField(blank=True, default="")
    photo_url = models.URLField(blank=True, default="")

    # Professional
    current_title = models.CharField(max_length=255, blank=True, default="")
    current_company = models.CharField(max_length=255, blank=True, default="")
    location_city = models.CharField(max_length=100, blank=True, default="")
    location_country = models.CharField(max_length=100, blank=True, default="")
    location_region = models.CharField(max_length=100, blank=True, default="")
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    seniority_level = models.CharField(max_length=50, blank=True, default="")
    skills = models.JSONField(default=list, blank=True)          # ["Python","AWS",...]
    certifications = models.JSONField(default=list, blank=True)
    clearance_level = models.CharField(max_length=100, blank=True, default="")
    licenses = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)            # free-form labels
    notes = models.TextField(blank=True, default="")
    resume_url = models.URLField(blank=True, default="")

    # Source & stage
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="other")
    source_detail = models.CharField(max_length=255, blank=True, default="")  # e.g. event name
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="identified")
    recruiter = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sourcing_owned_prospects"
    )

    # Consent
    consent_status = models.CharField(max_length=20, choices=CONSENT_STATUS_CHOICES, default="pending")
    consent_given_at = models.DateTimeField(null=True, blank=True)
    consent_expires_at = models.DateTimeField(null=True, blank=True)
    consent_source = models.CharField(max_length=255, blank=True, default="")
    prefers_email = models.BooleanField(default=True)
    prefers_sms = models.BooleanField(default=False)
    prefers_whatsapp = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=10, blank=True, default="en")
    unsubscribed = models.BooleanField(default=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    # Scoring
    engagement_score = models.FloatField(default=0.0)        # 0-100
    reengage_score = models.FloatField(default=0.0)          # "ready to re-engage" score
    profile_completeness = models.FloatField(default=0.0)    # 0-100
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    last_replied_at = models.DateTimeField(null=True, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)

    # Conversion tracking
    converted_to_candidate_id = models.UUIDField(null=True, blank=True)
    converted_to_application_id = models.UUIDField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    conversion_job = models.ForeignKey(
        "jobs.Job", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sourced_conversions"
    )

    # Alumni / silver medalist / passive flags
    is_alumni = models.BooleanField(default=False)
    is_silver_medalist = models.BooleanField(default=False)
    is_passive = models.BooleanField(default=True)
    is_contractor = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sourcing_prospects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "stage"]),
            models.Index(fields=["tenant", "source"]),
            models.Index(fields=["tenant", "recruiter"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.stage})"


# ── 2. Talent Pool ────────────────────────────────────────────────────────────

class TalentPool(models.Model):
    """
    A named grouping of prospects with filtering metadata.
    Pool types cover all the listed categories from the spec.
    """

    POOL_TYPE_CHOICES = [
        ("general", "General"),
        ("skill", "Skill-based"),
        ("geography", "Geography-based"),
        ("seniority", "Seniority-based"),
        ("clearance", "Clearance / Security"),
        ("license", "License / Certification"),
        ("source", "Source-based"),
        ("silver_medalist", "Silver Medalists"),
        ("alumni", "Alumni"),
        ("event", "Event Leads"),
        ("campus", "Campus Leads"),
        ("contractor", "Contractor / Freelancer"),
        ("passive", "Passive Candidates"),
        ("talent_community", "Talent Community"),
        ("custom", "Custom Segment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sourcing_talent_pools")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    pool_type = models.CharField(max_length=30, choices=POOL_TYPE_CHOICES, default="general")
    color = models.CharField(max_length=7, default="#6366F1")
    icon = models.CharField(max_length=10, blank=True, default="")
    owner = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sourcing_owned_pools"
    )

    # Criteria for auto-membership (stored as JSON filter spec)
    auto_criteria = models.JSONField(default=dict, blank=True)
    is_dynamic = models.BooleanField(default=False)   # auto-adds matching prospects
    is_active = models.BooleanField(default=True)
    is_private = models.BooleanField(default=False)

    # Health metrics (updated by background job / snapshot)
    member_count = models.PositiveIntegerField(default=0)
    engaged_count = models.PositiveIntegerField(default=0)
    converted_count = models.PositiveIntegerField(default=0)
    health_score = models.FloatField(default=0.0)   # 0-100
    last_health_calc_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sourcing_talent_pools"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PoolMembership(models.Model):
    """M2M through table: Prospect ↔ TalentPool with per-member metadata."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("exited", "Exited"),
        ("converted", "Converted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(TalentPool, on_delete=models.CASCADE, related_name="memberships")
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="pool_memberships")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    added_by = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sourcing_pool_additions"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")
    engagement_score = models.FloatField(default=0.0)

    class Meta:
        db_table = "sourcing_pool_memberships"
        unique_together = [("pool", "prospect")]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.prospect} → {self.pool}"


# ── 3. Pool Health Snapshot ───────────────────────────────────────────────────

class PoolHealthSnapshot(models.Model):
    """Daily/weekly snapshot of pool health metrics for trend charts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(TalentPool, on_delete=models.CASCADE, related_name="health_snapshots")
    snapshot_date = models.DateField()
    member_count = models.PositiveIntegerField(default=0)
    new_additions = models.PositiveIntegerField(default=0)
    engaged_count = models.PositiveIntegerField(default=0)
    converted_count = models.PositiveIntegerField(default=0)
    health_score = models.FloatField(default=0.0)
    avg_engagement_score = models.FloatField(default=0.0)

    class Meta:
        db_table = "sourcing_pool_health_snapshots"
        unique_together = [("pool", "snapshot_date")]
        ordering = ["-snapshot_date"]


# ── 4. Follow-up Task ─────────────────────────────────────────────────────────

class FollowUpTask(models.Model):
    """Recruiter task tied to a prospect (call, email, LinkedIn message, etc.)."""

    TASK_TYPE_CHOICES = [
        ("email", "Send Email"),
        ("call", "Phone Call"),
        ("linkedin", "LinkedIn Message"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("note", "Add Note"),
        ("meeting", "Schedule Meeting"),
        ("research", "Research / Profile"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("skipped", "Skipped"),
        ("overdue", "Overdue"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sourcing_tasks")
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="follow_up_tasks")
    assigned_to = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sourcing_tasks"
    )
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default="email")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    priority = models.CharField(max_length=10, choices=[("low","Low"),("medium","Medium"),("high","High")], default="medium")
    cadence_step = models.PositiveSmallIntegerField(null=True, blank=True)  # step # in cadence if part of one

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sourcing_follow_up_tasks"
        ordering = ["due_at"]

    def __str__(self):
        return f"{self.task_type}: {self.prospect} — {self.title}"


# ── 5. Nurture Sequence (Cadence) ─────────────────────────────────────────────

class NurtureSequence(models.Model):
    """
    A named multi-step outreach cadence (e.g. 7-day passive candidate sequence).
    """

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("linkedin", "LinkedIn"),
        ("multi", "Multi-channel"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sourcing_nurture_sequences")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    is_active = models.BooleanField(default=True)
    total_steps = models.PositiveSmallIntegerField(default=0)
    target_pool = models.ForeignKey(
        TalentPool, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sequences"
    )
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sourcing_created_sequences"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sourcing_nurture_sequences"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SequenceStep(models.Model):
    """A single step in a nurture sequence."""

    STEP_TYPE_CHOICES = [
        ("email", "Send Email"),
        ("sms", "Send SMS"),
        ("whatsapp", "Send WhatsApp"),
        ("linkedin", "LinkedIn Message"),
        ("task", "Manual Task"),
        ("wait", "Wait / Delay"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(NurtureSequence, on_delete=models.CASCADE, related_name="steps")
    step_number = models.PositiveSmallIntegerField()
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default="email")
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")        # supports {{first_name}} merge tags
    delay_days = models.PositiveSmallIntegerField(default=0)   # days after previous step
    delay_hours = models.PositiveSmallIntegerField(default=0)
    condition = models.CharField(max_length=50, blank=True, default="")  # e.g. "no_reply"
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sourcing_sequence_steps"
        ordering = ["sequence", "step_number"]
        unique_together = [("sequence", "step_number")]

    def __str__(self):
        return f"{self.sequence.name} — Step {self.step_number}"


class SequenceEnrollment(models.Model):
    """Tracks a prospect's progress through a nurture sequence."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("exited", "Exited (replied/converted)"),
        ("unsubscribed", "Unsubscribed"),
        ("bounced", "Bounced"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(NurtureSequence, on_delete=models.CASCADE, related_name="enrollments")
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="sequence_enrollments")
    current_step = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    next_send_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    exited_reason = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "sourcing_sequence_enrollments"
        unique_together = [("sequence", "prospect")]
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.prospect} in {self.sequence} (step {self.current_step})"


# ── 6. Outreach Campaign ──────────────────────────────────────────────────────

class OutreachCampaign(models.Model):
    """
    A bulk personalized outreach campaign targeting a pool or segment.
    Supports email / SMS / WhatsApp by region.
    """

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("linkedin", "LinkedIn InMail"),
        ("multi", "Multi-channel"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("paused", "Paused"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="sourcing_outreach_campaigns")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Targeting
    target_pool = models.ForeignKey(
        TalentPool, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="campaigns"
    )
    target_segment = models.ForeignKey(
        "SavedSegment", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="campaigns"
    )
    region_filter = models.CharField(max_length=100, blank=True, default="")   # e.g. "EMEA"
    language_filter = models.CharField(max_length=10, blank=True, default="")  # e.g. "es"

    # Content
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")           # merge-tag aware
    from_name = models.CharField(max_length=100, blank=True, default="")
    from_email = models.EmailField(blank=True, default="")
    reply_to = models.EmailField(blank=True, default="")
    utm_campaign = models.CharField(max_length=100, blank=True, default="")

    # Schedule
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Metrics
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    opened_count = models.PositiveIntegerField(default=0)
    clicked_count = models.PositiveIntegerField(default=0)
    replied_count = models.PositiveIntegerField(default=0)
    bounced_count = models.PositiveIntegerField(default=0)
    unsubscribed_count = models.PositiveIntegerField(default=0)
    converted_count = models.PositiveIntegerField(default=0)   # replied → became applicant

    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_campaigns"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sourcing_outreach_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class OutreachMessage(models.Model):
    """
    An individual outreach message sent to a single prospect
    (either standalone or part of a campaign/sequence step).
    """

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("linkedin", "LinkedIn"),
    ]

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("opened", "Opened"),
        ("clicked", "Clicked"),
        ("replied", "Replied"),
        ("bounced", "Bounced"),
        ("failed", "Failed"),
        ("unsubscribed", "Unsubscribed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="outreach_messages")
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="outreach_messages")
    campaign = models.ForeignKey(
        OutreachCampaign, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="messages"
    )
    sequence_step = models.ForeignKey(
        SequenceStep, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="messages"
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")           # personalized body
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    reply_body = models.TextField(blank=True, default="")
    sent_by = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sent_outreach_messages"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sourcing_outreach_messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel} → {self.prospect} ({self.status})"


# ── 7. Saved Segment ──────────────────────────────────────────────────────────

class SavedSegment(models.Model):
    """
    A reusable filter query saved as a named segment.
    Used for campaigns, analytics, and pool auto-criteria.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="saved_segments")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    filters = models.JSONField(default=dict)   # {stage: "engaged", skills__contains: "Python", ...}
    is_active = models.BooleanField(default=True)
    prospect_count = models.PositiveIntegerField(default=0)   # cached count
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="saved_segments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sourcing_saved_segments"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ── 8. Do Not Contact / Suppression ──────────────────────────────────────────

class DoNotContact(models.Model):
    """Global suppression list entry. Checked before any outreach."""

    REASON_CHOICES = [
        ("opted_out", "Opted Out"),
        ("legal_hold", "Legal Hold"),
        ("competitor", "Competitor Employee"),
        ("harassment", "Harassment Report"),
        ("do_not_hire", "Do Not Hire"),
        ("manual", "Manual Entry"),
        ("bounced", "Hard Bounce"),
        ("spam_complaint", "Spam Complaint"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="dnc_list")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    prospect = models.ForeignKey(
        Prospect, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="dnc_entries"
    )
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default="opted_out")
    notes = models.TextField(blank=True, default="")
    added_by = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sourcing_dnc_additions"
    )
    expires_at = models.DateTimeField(null=True, blank=True)   # null = permanent
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sourcing_do_not_contact"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DNC: {self.email or self.phone} ({self.reason})"


# ── 9. Warm Intro / Referral Relationship Graph ───────────────────────────────

class WarmIntro(models.Model):
    """
    Tracks a warm introduction: who introduced a prospect, via what channel.
    Forms the referral relationship graph.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Ask"),
        ("requested", "Intro Requested"),
        ("made", "Intro Made"),
        ("converted", "Converted to Applicant"),
        ("declined", "Declined"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="warm_intros")
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="warm_intros")
    introducer_employee = models.ForeignKey(
        "accounts.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="introductions_made"
    )
    introducer_name = models.CharField(max_length=255, blank=True, default="")  # if not a User
    introducer_email = models.EmailField(blank=True, default="")
    relationship = models.CharField(max_length=100, blank=True, default="")  # e.g. "Former colleague"
    channel = models.CharField(max_length=50, blank=True, default="")         # e.g. "LinkedIn"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True, default="")
    requested_at = models.DateTimeField(null=True, blank=True)
    made_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sourcing_warm_intros"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Intro: {self.introducer_name or self.introducer_employee} → {self.prospect}"


# ── 10. Prospect Preference Center ───────────────────────────────────────────

class CandidatePreference(models.Model):
    """
    Prospect / candidate communication and job preferences.
    Powers consent-aware sourcing and personalization.
    """

    FREQUENCY_CHOICES = [
        ("immediately", "Immediately"),
        ("weekly", "Weekly Digest"),
        ("monthly", "Monthly"),
        ("never", "Never"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prospect = models.OneToOneField(Prospect, on_delete=models.CASCADE, related_name="preferences")
    job_alert_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="weekly")
    preferred_job_types = models.JSONField(default=list, blank=True)   # ["full_time","contract"]
    preferred_locations = models.JSONField(default=list, blank=True)
    preferred_roles = models.JSONField(default=list, blank=True)
    preferred_salary_min = models.PositiveIntegerField(null=True, blank=True)
    open_to_relocation = models.BooleanField(default=False)
    open_to_remote = models.BooleanField(default=True)
    available_from = models.DateField(null=True, blank=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sourcing_candidate_preferences"

    def __str__(self):
        return f"Preferences: {self.prospect}"


# ── 11. Similar-Candidate Suggestion ─────────────────────────────────────────

class SimilarProspectSuggestion(models.Model):
    """
    Records AI/heuristic suggestions of similar prospects.
    Enables rediscovery of old candidates and look-alike sourcing.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="prospect_suggestions")
    source_prospect = models.ForeignKey(
        Prospect, on_delete=models.CASCADE, related_name="similar_suggestions_from"
    )
    suggested_prospect = models.ForeignKey(
        Prospect, on_delete=models.CASCADE, related_name="similar_suggestions_to"
    )
    similarity_score = models.FloatField(default=0.0)   # 0-1
    reasons = models.JSONField(default=list, blank=True)  # ["Same skills","Same location"]
    is_dismissed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sourcing_similar_prospect_suggestions"
        unique_together = [("source_prospect", "suggested_prospect")]
        ordering = ["-similarity_score"]


# ── 12. Outreach Analytics Snapshot ──────────────────────────────────────────

class OutreachAnalyticsSnapshot(models.Model):
    """
    Daily/weekly snapshot of outreach performance metrics per channel and source.
    Powers source-pipeline ROI and reply-rate analytics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="outreach_snapshots")
    snapshot_date = models.DateField()
    channel = models.CharField(max_length=20, blank=True, default="")
    source = models.CharField(max_length=30, blank=True, default="")

    # Volume
    sent = models.PositiveIntegerField(default=0)
    delivered = models.PositiveIntegerField(default=0)
    opened = models.PositiveIntegerField(default=0)
    clicked = models.PositiveIntegerField(default=0)
    replied = models.PositiveIntegerField(default=0)
    bounced = models.PositiveIntegerField(default=0)
    unsubscribed = models.PositiveIntegerField(default=0)

    # Conversion funnel
    prospects_contacted = models.PositiveIntegerField(default=0)
    prospects_engaged = models.PositiveIntegerField(default=0)
    prospects_converted = models.PositiveIntegerField(default=0)   # became applicants

    # ROI
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hires_attributed = models.PositiveIntegerField(default=0)
    cost_per_hire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "sourcing_outreach_analytics_snapshots"
        ordering = ["-snapshot_date"]
        unique_together = [("tenant", "snapshot_date", "channel", "source")]
