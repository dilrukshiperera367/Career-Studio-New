"""Candidates app — Candidates, identities, resumes, skills, experiences."""

import uuid
from django.db import models


class Candidate(models.Model):
    """A person who may apply to jobs. Persistent identity across applications."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("merged", "Merged"),
        ("deleted", "Deleted"),
    ]

    POOL_STATUS_CHOICES = [
        ("new", "New"),
        ("active", "Active"),
        ("pipeline", "In Pipeline"),
        ("hired", "Hired"),
        ("archived", "Archived"),
        ("gdpr_deleted", "GDPR Deleted"),
    ]

    TALENT_TIER_CHOICES = [
        ("none", "None"),
        ("silver", "Silver"),
        ("gold", "Gold"),
        ("platinum", "Platinum"),
    ]

    AVAILABILITY_CHOICES = [
        ("immediate", "Immediately Available"),
        ("2_weeks", "2 Weeks Notice"),
        ("1_month", "1 Month Notice"),
        ("3_months", "3 Months Notice"),
        ("not_looking", "Not Looking"),
    ]

    PREFERRED_CONTACT_CHOICES = [
        ("email", "Email"),
        ("phone", "Phone"),
        ("whatsapp", "WhatsApp"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidates")
    full_name = models.CharField(max_length=300)
    primary_email = models.EmailField(blank=True, null=True)
    primary_phone = models.CharField(max_length=30, blank=True, default="")
    headline = models.CharField(max_length=300, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    location_normalized = models.JSONField(
        null=True, blank=True,
        help_text='{"city": "...", "country_code": "..."}'
    )
    linkedin_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")
    portfolio_url = models.URLField(blank=True, default="")

    # Derived fields (computed by parsing pipeline)
    total_experience_years = models.FloatField(null=True, blank=True)
    most_recent_title = models.CharField(max_length=200, blank=True, default="")
    most_recent_company = models.CharField(max_length=200, blank=True, default="")
    recency_score = models.FloatField(null=True, blank=True)
    highest_education = models.CharField(max_length=50, blank=True, default="",
        help_text="PhD, Masters, Bachelors, Associate, High School")
    resume_completeness = models.FloatField(null=True, blank=True,
        help_text="0-100 how complete the parsed profile is")

    source = models.CharField(max_length=100, blank=True, default="direct")
    tags = models.JSONField(default=list, blank=True)

    # Talent pool & lifecycle (Features 1-12)
    pool_status = models.CharField(max_length=20, choices=POOL_STATUS_CHOICES, default="new")
    talent_tier = models.CharField(max_length=20, choices=TALENT_TIER_CHOICES, default="none")
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default="immediate")
    preferred_contact = models.CharField(max_length=20, choices=PREFERRED_CONTACT_CHOICES, default="email")
    rating = models.IntegerField(null=True, blank=True, help_text="1-5 star rating")
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_candidates"
    )

    # GDPR / Consent (Feature 10)
    consent_given_at = models.DateTimeField(null=True, blank=True)
    consent_expires_at = models.DateTimeField(null=True, blank=True)
    data_retention_until = models.DateTimeField(null=True, blank=True)
    gdpr_deletion_requested_at = models.DateTimeField(null=True, blank=True)

    # CRM depth fields (talent_crm integration)
    crm_stage = models.CharField(
        max_length=30,
        choices=[
            ("prospect", "Prospect"),
            ("engaged", "Engaged"),
            ("nurturing", "Nurturing"),
            ("warm", "Warm"),
            ("converted", "Converted"),
            ("inactive", "Inactive"),
        ],
        blank=True, default="",
    )
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    crm_notes = models.TextField(blank=True, default="")
    do_not_contact = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    redirect_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="If merged, points to the target candidate"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "candidates"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "primary_email"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "pool_status"]),
            models.Index(fields=["tenant", "talent_tier"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.primary_email or 'no email'})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete_many([
            f'candidates:list:{self.tenant_id}',
            f'dashboard:{self.tenant_id}',
        ])


class CandidateIdentity(models.Model):
    """Identity records for dedup: email, phone, linkedin, etc."""

    IDENTITY_TYPES = [
        ("email", "Email"),
        ("phone", "Phone"),
        ("linkedin", "LinkedIn"),
        ("github", "GitHub"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="identities")
    identity_type = models.CharField(max_length=20, choices=IDENTITY_TYPES)
    identity_value = models.CharField(max_length=500)

    class Meta:
        db_table = "candidate_identities"
        unique_together = [("tenant", "identity_type", "identity_value")]
        indexes = [
            models.Index(fields=["tenant", "identity_value"]),
        ]

    def __str__(self):
        return f"{self.identity_type}: {self.identity_value}"


class ResumeDocument(models.Model):
    """A versioned resume file + parse results."""

    STATUS_CHOICES = [
        ("pending_parse", "Pending Parse"),
        ("parsing", "Parsing"),
        ("parsed", "Parsed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="resumes")
    version = models.IntegerField(default=1)
    file_url = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64, blank=True, default="")
    file_type = models.CharField(max_length=50, default="application/pdf")

    raw_text = models.TextField(blank=True, default="")
    clean_text = models.TextField(blank=True, default="")
    parsed_json = models.JSONField(null=True, blank=True)

    parse_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_parse")
    parse_error = models.TextField(blank=True, default="")
    parse_confidence = models.FloatField(null=True, blank=True)
    parse_warnings = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "resume_documents"
        ordering = ["-version"]
        indexes = [
            models.Index(fields=["tenant", "candidate", "version"]),
        ]

    def __str__(self):
        return f"Resume v{self.version} — {self.candidate.full_name}"


class CandidateSkill(models.Model):
    """Extracted & normalized skill for a candidate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="skills")
    skill = models.ForeignKey(
        "taxonomy.SkillTaxonomy", on_delete=models.CASCADE, related_name="candidate_skills"
    )
    canonical_name = models.CharField(max_length=200)
    confidence = models.FloatField(default=1.0)
    years_used = models.FloatField(null=True, blank=True)
    evidence = models.JSONField(default=list, blank=True, help_text="Matched text excerpts")
    source_section = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_skills"
        unique_together = [("candidate", "skill")]

    def __str__(self):
        return f"{self.canonical_name} ({self.candidate.full_name})"


class CandidateExperience(models.Model):
    """Extracted work experience entry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="experiences")
    company_name = models.CharField(max_length=300)
    title = models.CharField(max_length=300)
    normalized_title = models.CharField(max_length=300, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    raw_block = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_experiences"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.title} at {self.company_name}"


class CandidateEducation(models.Model):
    """Extracted education entry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=300)
    degree = models.CharField(max_length=200, blank=True, default="")
    field_of_study = models.CharField(max_length=200, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_education"
        ordering = ["-end_date"]

    def __str__(self):
        return f"{self.degree} — {self.institution}"


class MergeAudit(models.Model):
    """Audit trail for candidate merges (never delete)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    from_candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="merge_sources"
    )
    to_candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="merge_targets"
    )
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "merge_audits"

    def __str__(self):
        return f"Merge {self.from_candidate_id} → {self.to_candidate_id}"


class CandidateNote(models.Model):
    """Note/comment on a candidate — supports threading via parent_note."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="candidate_notes"
    )
    content = models.TextField()
    is_internal = models.BooleanField(default=True, help_text="Internal = not visible to candidate")
    mentions = models.JSONField(default=list, blank=True, help_text="User IDs mentioned via @")
    parent_note = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "candidate_notes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "candidate", "created_at"]),
        ]

    def __str__(self):
        return f"Note on {self.candidate.full_name} by {self.author}"


class CandidateCertification(models.Model):
    """Professional certification extracted or manually added."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=300)
    issuer = models.CharField(max_length=300, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_certifications"
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.name} — {self.candidate.full_name}"


class DataSubjectRequest(models.Model):
    """
    GDPR Data Subject Request (#49, #50).

    Tracks requests from data subjects exercising their rights under GDPR:
    - Right of access (access) — export all data held about them
    - Right to erasure (erasure) — delete / anonymize their data
    - Data portability (portability) — machine-readable export
    - Rectification (rectification) — correct inaccurate data
    """

    REQUEST_TYPE_CHOICES = [
        ("access", "Right of Access"),
        ("erasure", "Right to Erasure"),
        ("portability", "Data Portability"),
        ("rectification", "Rectification"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="data_subject_requests"
    )
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    requester_email = models.EmailField(help_text="Email of the data subject making the request")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    deadline = models.DateField(
        null=True, blank=True,
        help_text="Statutory deadline (30 days from receipt under GDPR)"
    )
    submitted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="submitted_dsrs"
    )
    processed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processed_dsrs"
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_subject_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["requester_email"]),
        ]

    def __str__(self):
        return f"{self.request_type} request from {self.requester_email} ({self.status})"


class CandidateFollowUpTask(models.Model):
    """CRM-style follow-up task for a candidate owned by a recruiter."""

    PRIORITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("done", "Done"),
        ("snoozed", "Snoozed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_followup_tasks")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="followup_tasks")
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="candidate_tasks",
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")
    due_at = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "candidate_followup_tasks"
        ordering = ["due_at", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "candidate", "status"]),
            models.Index(fields=["tenant", "owner", "status"]),
        ]

    def __str__(self):
        return f"Task: {self.title} ({self.status})"


class CandidateOutreachLog(models.Model):
    """
    Records every outreach touchpoint: email, call, LinkedIn message, etc.
    Used for CRM-style engagement tracking and nurture analytics.
    """

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("phone", "Phone"),
        ("linkedin", "LinkedIn"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("in_person", "In Person"),
        ("other", "Other"),
    ]

    OUTCOME_CHOICES = [
        ("no_response", "No Response"),
        ("positive", "Positive Response"),
        ("negative", "Not Interested"),
        ("callback_requested", "Callback Requested"),
        ("meeting_booked", "Meeting Booked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="outreach_logs")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="outreach_logs")
    sender = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="outreach_logs",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES, default="no_response")
    notes = models.TextField(blank=True, default="")
    contacted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_outreach_logs"
        ordering = ["-contacted_at"]
        indexes = [
            models.Index(fields=["tenant", "candidate", "contacted_at"]),
            models.Index(fields=["tenant", "sender"]),
        ]

    def __str__(self):
        return f"{self.channel} outreach to {self.candidate_id} ({self.outcome})"
