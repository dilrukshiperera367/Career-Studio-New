"""Portal app — Candidate Experience Portal 2.0 models."""

import uuid
from django.db import models


# ---------------------------------------------------------------------------
# Existing models (Feature 1 portal baseline) — preserved verbatim
# ---------------------------------------------------------------------------

class JobAlert(models.Model):
    """Candidate subscribes to be notified when matching jobs are posted."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_alerts")
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True, default="")
    keywords = models.JSONField(default=list, blank=True, help_text='["Python", "Backend"]')
    department = models.CharField(max_length=150, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    employment_type = models.CharField(max_length=30, blank=True, default="")
    salary_min = models.IntegerField(null=True, blank=True)
    frequency = models.CharField(
        max_length=20,
        choices=[("instant", "Instant"), ("daily", "Daily"), ("weekly", "Weekly")],
        default="weekly",
    )
    is_active = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    unsubscribe_token = models.CharField(max_length=80, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_alerts"
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self):
        return f"Alert: {self.email} ({', '.join(self.keywords or [])})"


class CandidateFeedback(models.Model):
    """Post-rejection survey — candidate rates their experience."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="feedback")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True
    )
    overall_rating = models.IntegerField(help_text="1-5 stars")
    comments = models.TextField(blank=True, default="")
    would_apply_again = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_feedback"

    def __str__(self):
        return f"Feedback {self.overall_rating}/5 from {self.candidate}"


class PortalToken(models.Model):
    """Token-based access for candidate self-service (no login required)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="portal_tokens")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True
    )
    token = models.CharField(max_length=100, unique=True, db_index=True)
    purpose = models.CharField(
        max_length=50,
        help_text=(
            "status_check, document_upload, self_schedule, offer_review, feedback, "
            "profile_update, withdraw, nps_survey, reschedule, prep_packet"
        ),
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "portal_tokens"

    def __str__(self):
        return f"Token ({self.purpose}) for {self.candidate}"


class SavedApplicationDraft(models.Model):
    """
    Candidate's partially-filled application draft — auto-saved from the portal.
    Supports anonymous (session key) and known candidates.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="draft_applications")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="application_drafts",
        null=True, blank=True,
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="application_drafts")
    session_key = models.CharField(max_length=100, blank=True, default="",
        help_text="Anonymous session key for unauthenticated users")
    draft_data = models.JSONField(default=dict, blank=True)
    resume_file_url = models.CharField(max_length=500, blank=True, default="")
    autofill_source = models.CharField(
        max_length=30, blank=True, default="",
        help_text="manual, resume_parse, history",
    )
    completion_pct = models.IntegerField(default=0, help_text="0-100 progress percentage")
    last_saved_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "saved_application_drafts"
        ordering = ["-last_saved_at"]
        indexes = [
            models.Index(fields=["tenant", "job"]),
            models.Index(fields=["session_key"]),
        ]

    def __str__(self):
        return f"Draft: {self.job_id} ({self.candidate_id or self.session_key})"


class CandidateNPS(models.Model):
    """
    Net Promoter Score survey sent to candidates at key lifecycle events.
    Tracks employer brand perception.
    """

    EVENT_CHOICES = [
        ("applied", "After Applying"),
        ("interviewed", "After Interview"),
        ("offer_received", "After Offer"),
        ("rejected", "After Rejection"),
        ("hired", "After Joining"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_nps")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="nps_responses"
    )
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="nps_responses",
    )
    event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    score = models.IntegerField(help_text="0-10 NPS score")
    comment = models.TextField(blank=True, default="")
    responded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_nps"
        ordering = ["-responded_at"]
        indexes = [
            models.Index(fields=["tenant", "event"]),
        ]

    def __str__(self):
        return f"NPS {self.score}/10 — {self.event}"


class AccessibilityPreference(models.Model):
    """
    Candidate's declared accessibility needs for interviews and assessments.
    WCAG 2.2 compliance — stored separately to avoid PII leakage.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="accessibility_prefs")
    candidate = models.OneToOneField(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="accessibility_preference"
    )
    needs = models.JSONField(
        default=list, blank=True,
        help_text='["screen_reader", "captions", "extra_time", "sign_language", "large_print", "braille", "interpreter"]'
    )
    notes = models.TextField(blank=True, default="")
    auth_alternative = models.CharField(
        max_length=30, blank=True, default="",
        help_text="magic_link, sms_otp, email_otp",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accessibility_preferences"

    def __str__(self):
        return f"A11y prefs for {self.candidate_id}"


# ---------------------------------------------------------------------------
# New Feature 5 models
# ---------------------------------------------------------------------------

class RoleApplicationForm(models.Model):
    """
    Role-based application form schema — different jobs can have different
    field sets, custom questions, knockout logic, and multi-language labels.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="application_forms")
    name = models.CharField(max_length=200)
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="application_form",
    )
    department = models.CharField(max_length=150, blank=True, default="")
    # Field schema: [{id, type, label, required, knockout, options, translations: {es: ..., fr: ...}}]
    fields = models.JSONField(default=list, blank=True)
    enable_autofill = models.BooleanField(default=True)
    one_click_threshold = models.IntegerField(
        default=80, help_text="Profile completeness % required for one-click apply"
    )
    supported_locales = models.JSONField(default=list, blank=True)
    legal_notices = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "role_application_forms"
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self):
        return f"Form: {self.name} ({self.tenant_id})"


class CandidateDashboardSession(models.Model):
    """
    Authenticated session for candidate self-service dashboard.
    Candidates log in via email magic link — no password required (WCAG 2.2 accessible auth).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="dashboard_sessions")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="dashboard_sessions"
    )
    session_token = models.CharField(max_length=128, unique=True, db_index=True)
    login_method = models.CharField(
        max_length=20, default="magic_link",
        help_text="magic_link, sms_otp, google_sso",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    expires_at = models.DateTimeField()
    last_activity_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_dashboard_sessions"
        indexes = [models.Index(fields=["tenant", "candidate"])]

    def __str__(self):
        return f"Session for {self.candidate_id}"


class ApplicationStageConfig(models.Model):
    """
    Per-stage explanation and expected timeline for candidate-facing transparency.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="stage_configs")
    stage = models.OneToOneField(
        "jobs.PipelineStage", on_delete=models.CASCADE, related_name="candidate_config"
    )
    candidate_label = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    expected_timeline_days = models.IntegerField(null=True, blank=True)
    next_steps_message = models.TextField(blank=True, default="")
    translations = models.JSONField(default=dict, blank=True)
    show_interviewer_names = models.BooleanField(default=False)
    show_timeline = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "application_stage_configs"

    def __str__(self):
        return f"StageConfig: {self.stage_id}"


class InterviewPrepPacket(models.Model):
    """
    Interview preparation materials sent to candidate before an interview.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="prep_packets")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="prep_packets"
    )
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="prep_packets",
        null=True, blank=True,
    )
    title = models.CharField(max_length=200, blank=True, default="")
    sections = models.JSONField(default=list, blank=True,
        help_text='[{type: "tips"|"logistics"|"company"|"role"|"accessibility", content: "..."}]')
    logistics = models.JSONField(default=dict, blank=True)
    accessibility_notes = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    help_contact_name = models.CharField(max_length=200, blank=True, default="")
    help_contact_email = models.EmailField(blank=True, default="")
    help_contact_phone = models.CharField(max_length=30, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interview_prep_packets"
        indexes = [models.Index(fields=["tenant", "application"])]

    def __str__(self):
        return f"PrepPacket for application {self.application_id}"


class SelfRescheduleRule(models.Model):
    """
    Configures when and how many times a candidate may self-reschedule an interview.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="reschedule_rules")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reschedule_rules",
    )
    max_reschedules = models.IntegerField(default=2)
    min_hours_before = models.IntegerField(default=24)
    allowed_interview_types = models.JSONField(default=list, blank=True)
    require_reason = models.BooleanField(default=False)
    notify_recruiter = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_reschedule_rules"

    def __str__(self):
        return f"RescheduleRule: max={self.max_reschedules} ({self.tenant_id})"


class CandidateWithdrawal(models.Model):
    """Candidate self-withdraws from an application through the portal."""

    REASON_CHOICES = [
        ("accepted_other_offer", "Accepted another offer"),
        ("role_not_right", "Role is not the right fit"),
        ("location", "Location / remote policy"),
        ("compensation", "Compensation"),
        ("personal", "Personal reasons"),
        ("too_long", "Process taking too long"),
        ("no_response", "No response from company"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    application = models.OneToOneField(
        "applications.Application", on_delete=models.CASCADE, related_name="withdrawal"
    )
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, blank=True, default="")
    reason_detail = models.TextField(blank=True, default="")
    would_apply_future = models.BooleanField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_withdrawals"

    def __str__(self):
        return f"Withdrawal: app {self.application_id}"


class MissingDocumentRequest(models.Model):
    """Recruiter requests a specific document from a candidate via portal link."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("uploaded", "Uploaded"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="doc_requests")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="doc_requests"
    )
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_doc_requests",
    )
    document_type = models.CharField(max_length=100)
    instructions = models.TextField(blank=True, default="")
    upload_token = models.CharField(max_length=128, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    uploaded_file_url = models.CharField(max_length=500, blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "missing_document_requests"
        indexes = [models.Index(fields=["tenant", "application"])]

    def __str__(self):
        return f"DocRequest: {self.document_type} for app {self.application_id}"


class AccommodationRequest(models.Model):
    """
    Candidate requests a workplace or interview accommodation.
    Covers WCAG 2.2 interview accessibility preferences plus HR accommodation workflow.
    """

    TYPE_CHOICES = [
        ("interview_accessibility", "Interview Accessibility"),
        ("assessment_accessibility", "Assessment Accessibility"),
        ("workplace_accommodation", "Workplace Accommodation"),
        ("communication_preference", "Communication Preference"),
        ("language_support", "Language Support"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("partially_approved", "Partially Approved"),
        ("declined", "Declined"),
        ("needs_info", "Needs More Information"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="accommodation_requests")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="accommodation_requests"
    )
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accommodation_requests",
    )
    accommodation_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    description = models.TextField()
    needs = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")
    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_accommodations",
    )
    reviewer_notes = models.TextField(blank=True, default="")
    approved_accommodations = models.JSONField(default=list, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accommodation_requests"
        indexes = [models.Index(fields=["tenant", "status"])]

    def __str__(self):
        return f"Accommodation: {self.accommodation_type} — {self.status}"


class TalentCommunityMember(models.Model):
    """
    Candidate joins the talent community (no open job, future interest).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="talent_community")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="community_memberships",
    )
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True, default="")
    interests = models.JSONField(default=list, blank=True)
    preferred_roles = models.JSONField(default=list, blank=True)
    preferred_locations = models.JSONField(default=list, blank=True)
    open_to_relocation = models.BooleanField(default=False)
    linkedin_url = models.CharField(max_length=300, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("unsubscribed", "Unsubscribed"), ("converted", "Converted")],
        default="active",
    )
    assigned_recruiter = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="community_members",
    )
    consent_marketing = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)
    unsubscribe_token = models.CharField(max_length=80, blank=True, default="", db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "talent_community_members"
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"Community: {self.email} ({self.tenant_id})"


class CandidateEvent(models.Model):
    """Recruiting event that candidates can register for from the portal."""

    EVENT_TYPE_CHOICES = [
        ("info_session", "Info Session"),
        ("open_day", "Open Day"),
        ("hackathon", "Hackathon"),
        ("career_fair", "Career Fair"),
        ("webinar", "Webinar"),
        ("networking", "Networking"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_events")
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, default="info_session")
    description = models.TextField(blank=True, default="")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=300, blank=True, default="")
    is_virtual = models.BooleanField(default=True)
    virtual_link = models.CharField(max_length=500, blank=True, default="")
    max_registrants = models.IntegerField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    accessibility_info = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_events"
        indexes = [models.Index(fields=["tenant", "starts_at"])]

    def __str__(self):
        return f"Event: {self.title}"


class EventRegistration(models.Model):
    """Candidate registers for a recruiting event."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    event = models.ForeignKey(CandidateEvent, on_delete=models.CASCADE, related_name="registrations")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="event_registrations",
    )
    email = models.EmailField()
    name = models.CharField(max_length=200, blank=True, default="")
    accessibility_needs = models.JSONField(default=list, blank=True)
    attended = models.BooleanField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_registrations"
        unique_together = [("event", "email")]

    def __str__(self):
        return f"Registration: {self.email} for {self.event_id}"


class HelpArticle(models.Model):
    """
    Candidate help center article. Supports multi-language content.
    WCAG 2.2 Consistent Help — always present in the same location.
    """

    CATEGORY_CHOICES = [
        ("application", "Application Process"),
        ("interview", "Interview Prep"),
        ("offer", "Offers & Contracts"),
        ("profile", "Your Profile"),
        ("privacy", "Privacy & Data"),
        ("accessibility", "Accessibility"),
        ("technical", "Technical Issues"),
        ("general", "General"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="help_articles",
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="general")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    content = models.TextField()
    translations = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    view_count = models.IntegerField(default=0)
    helpful_votes = models.IntegerField(default=0)
    unhelpful_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "help_articles"
        indexes = [
            models.Index(fields=["category", "is_published"]),
        ]

    def __str__(self):
        return self.title


class ConsentRecord(models.Model):
    """
    Granular consent tracking per candidate per purpose.
    Used by privacy/consent center self-service portal.
    """

    PURPOSE_CHOICES = [
        ("data_processing", "Processing application data"),
        ("marketing", "Marketing communications"),
        ("talent_pool", "Talent pool / future roles"),
        ("third_party_sharing", "Sharing with third parties"),
        ("profiling", "Automated profiling / AI scoring"),
        ("analytics", "Anonymous analytics"),
        ("cross_border_transfer", "Cross-border data transfer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="portal_consents")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="portal_consents"
    )
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    granted = models.BooleanField()
    granted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    locale = models.CharField(max_length=10, blank=True, default="en")
    notice_text = models.TextField(blank=True, default="")
    notice_version = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "portal_consent_records"
        indexes = [
            models.Index(fields=["tenant", "candidate", "purpose"]),
        ]

    def __str__(self):
        action = "granted" if self.granted else "withdrawn"
        return f"Consent {action}: {self.purpose} ({self.candidate_id})"


class DataSubjectRequest(models.Model):
    """
    GDPR / CCPA data subject requests submitted through the privacy center.
    """

    REQUEST_TYPE_CHOICES = [
        ("access", "Right of Access"),
        ("erasure", "Right to Erasure"),
        ("portability", "Data Portability"),
        ("rectification", "Rectification"),
        ("restriction", "Restriction of Processing"),
        ("objection", "Objection to Processing"),
    ]

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
        ("extended", "Extended (30+30 days)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="portal_dsr")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="portal_dsr",
    )
    email = models.EmailField()
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    handler = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="handled_dsr",
    )
    response_notes = models.TextField(blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portal_data_subject_requests"
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"DSR [{self.request_type}] {self.email} — {self.status}"


class RecruiterSafeRoute(models.Model):
    """
    Defines safe-routing rules: which recruiter a candidate should be directed to
    when they make contact from the portal.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="safe_routes")
    department = models.CharField(max_length=150, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    recruiter = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="safe_routes"
    )
    recruiter_display_name = models.CharField(max_length=200, blank=True, default="")
    recruiter_display_email = models.EmailField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recruiter_safe_routes"
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self):
        return f"SafeRoute: {self.department or 'all'} -> {self.recruiter_id}"
