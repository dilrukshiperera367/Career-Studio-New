"""Talent CRM — Talent pools, prospects, nurture sequences, outreach, consent."""

import uuid
from django.db import models


class TalentPool(models.Model):
    """A curated pool of candidates grouped by skill, geo, seniority, etc."""

    POOL_TYPE_CHOICES = [
        ("skill", "Skill-based"),
        ("geo", "Geography-based"),
        ("seniority", "Seniority-based"),
        ("silver_medalist", "Silver Medalists"),
        ("alumni", "Alumni"),
        ("talent_community", "Talent Community"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="talent_pools")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    pool_type = models.CharField(max_length=30, choices=POOL_TYPE_CHOICES, default="custom")
    owner = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_pools")
    segment_criteria = models.JSONField(default=dict, blank=True,
        help_text="Auto-segment rules: {'skills': [...], 'locations': [...], 'min_years_exp': 5}")
    is_active = models.BooleanField(default=True)
    member_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "talent_pools"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class TalentPoolMember(models.Model):
    """Membership record linking a candidate to a talent pool."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="pool_memberships")
    pool = models.ForeignKey(TalentPool, on_delete=models.CASCADE, related_name="members")
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="pool_memberships")
    added_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="pool_additions")
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "talent_pool_members"
        unique_together = [("pool", "candidate")]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.candidate} in {self.pool.name}"


class Prospect(models.Model):
    """A sourced lead that has not yet applied — CRM-style contact record."""

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("engaged", "Engaged"),
        ("applied", "Applied (Converted)"),
        ("declined", "Declined"),
        ("dormant", "Dormant"),
    ]

    SOURCE_CHOICES = [
        ("linkedin", "LinkedIn"),
        ("github", "GitHub"),
        ("referral", "Referral"),
        ("event", "Event"),
        ("inbound", "Inbound"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="prospects")
    email = models.EmailField(blank=True, default="")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    headline = models.CharField(max_length=500, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="other")
    source_metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    owner = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_prospects")
    target_role = models.CharField(max_length=255, blank=True, default="")
    target_job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="prospects")
    converted_candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.SET_NULL, null=True, blank=True, related_name="prospect_records"
    )
    sourcing_consent = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "prospects"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.status})"


class NurtureSequence(models.Model):
    """A drip campaign sequence of messages sent to prospects/candidates."""

    TRIGGER_CHOICES = [
        ("manual", "Manual Enroll"),
        ("pool_join", "Talent Pool Join"),
        ("prospect_created", "Prospect Created"),
        ("application_withdrawn", "Application Withdrawn"),
        ("silver_medalist", "Silver Medalist"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="crm_nurture_sequences")
    name = models.CharField(max_length=255)
    trigger = models.CharField(max_length=30, choices=TRIGGER_CHOICES, default="manual")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    steps_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_nurture_sequences"

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class NurtureStep(models.Model):
    """An individual step in a nurture sequence."""

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("linkedin", "LinkedIn InMail"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="crm_nurture_steps")
    sequence = models.ForeignKey(NurtureSequence, on_delete=models.CASCADE, related_name="steps")
    step_number = models.IntegerField(default=1)
    delay_days = models.IntegerField(default=0, help_text="Days after previous step to send")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    subject_line = models.CharField(max_length=500, blank=True, default="")
    body_template = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crm_nurture_steps"
        ordering = ["sequence", "step_number"]

    def __str__(self):
        return f"Step {self.step_number} of {self.sequence.name}"


class NurtureEnrollment(models.Model):
    """Tracking record for a prospect/candidate enrolled in a nurture sequence."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("unsubscribed", "Unsubscribed"),
        ("bounced", "Bounced"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="crm_enrollments")
    sequence = models.ForeignKey(NurtureSequence, on_delete=models.CASCADE, related_name="enrollments")
    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, null=True, blank=True, related_name="enrollments")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, null=True, blank=True, related_name="crm_enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    current_step = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    next_send_at = models.DateTimeField(null=True, blank=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "crm_nurture_enrollments"
        ordering = ["-enrolled_at"]

    def __str__(self):
        target = self.prospect or self.candidate
        return f"{target} enrolled in {self.sequence.name}"


class OutreachCampaign(models.Model):
    """Bulk outreach campaign to a talent pool or prospect segment."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("paused", "Paused"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="outreach_campaigns")
    name = models.CharField(max_length=255)
    talent_pool = models.ForeignKey(TalentPool, on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns")
    segment_query = models.JSONField(default=dict, blank=True)
    subject_line = models.CharField(max_length=500)
    body = models.TextField()
    channel = models.CharField(max_length=20, default="email")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    reply_count = models.IntegerField(default=0)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="outreach_campaigns")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "outreach_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.status})"


class DoNotContact(models.Model):
    """Suppression record — do not contact this email or candidate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="do_not_contact_list")
    email = models.EmailField()
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.SET_NULL, null=True, blank=True, related_name="dnc_records"
    )
    reason = models.CharField(max_length=255, blank=True, default="")
    added_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="dnc_additions")
    added_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "do_not_contact"
        unique_together = [("tenant", "email")]
        ordering = ["-added_at"]

    def __str__(self):
        return f"DNC: {self.email}"
