"""Assessments app — Full Screening & Assessment Orchestration Engine.

Covers:
- Pre-screen questionnaires + knockout questions + weighted screening rules
- Must-have requirement checks + credential/license verification
- Assessment catalog (coding, writing, case study, work sample, portfolio,
  language, SJT, async text/audio/video, vendor-ordered)
- Anti-cheating integrations + normalized results
- Alternate paths for accommodations + waivers/exemptions
- Screen decision reasons taxonomy + structured disqualification reasons
- Screen-review queues + blind review mode
- Audit trail for screening decisions
- Explainable match & screening logic
- Candidate appeal / reconsideration requests
"""

import uuid
from django.db import models


# ── Existing models (kept intact) ─────────────────────────────────────────────

class AssessmentVendor(models.Model):
    """An external assessment vendor (e.g. Codility, HackerRank, Criteria)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="assessment_vendors")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    api_base_url = models.URLField(blank=True, default="")
    api_key_encrypted = models.TextField(blank=True, default="", help_text="Encrypted vendor API key")
    webhook_secret_encrypted = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    supported_types = models.JSONField(
        default=list, blank=True,
        help_text='["coding", "cognitive", "personality", "work_sample"]'
    )
    # Anti-cheating capabilities this vendor supports
    anti_cheating_features = models.JSONField(
        default=list, blank=True,
        help_text='["proctoring", "plagiarism_detection", "tab_switch_detection", "id_verification"]'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_vendors"
        ordering = ["name"]
        unique_together = [("tenant", "slug")]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class AssessmentCatalogItem(models.Model):
    """A specific assessment product available from a vendor."""

    TYPE_CHOICES = [
        ("coding", "Coding Challenge"),
        ("writing", "Writing Assessment"),
        ("case_study", "Case Study"),
        ("work_sample", "Work Sample"),
        ("portfolio", "Portfolio Review"),
        ("cognitive", "Cognitive Ability"),
        ("personality", "Personality / Values"),
        ("language", "Language Proficiency"),
        ("sjt", "Situational Judgment Test"),
        ("async_text", "Async Text Response"),
        ("async_audio", "Async Audio Response"),
        ("async_video", "Async Video Response"),
        ("credential", "Credential / License Verification"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="assessment_catalog")
    vendor = models.ForeignKey(
        AssessmentVendor, on_delete=models.CASCADE, related_name="catalog_items"
    )
    name = models.CharField(max_length=255)
    assessment_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="custom")
    external_id = models.CharField(max_length=255, blank=True, default="", help_text="Vendor-side assessment ID")
    description = models.TextField(blank=True, default="")
    duration_minutes = models.IntegerField(null=True, blank=True)
    passing_score = models.FloatField(null=True, blank=True)
    max_score = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    cost_per_use = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    eu_ai_act_risk_level = models.CharField(
        max_length=20, default="limited",
        help_text="EU AI Act risk classification: minimal, limited, high"
    )
    requires_human_review = models.BooleanField(
        default=False, help_text="EU AI Act Annex III — human review mandatory for high-risk"
    )
    # Normalization
    normalization_method = models.CharField(
        max_length=30, default="percentile",
        help_text="How raw scores are normalized: percentile, z_score, band, raw"
    )
    norm_reference_group = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Reference population for normalization (e.g. 'SWE US 2024')"
    )
    # Anti-cheating
    anti_cheating_enabled = models.BooleanField(default=False)
    anti_cheating_config = models.JSONField(
        default=dict, blank=True,
        help_text='{"proctoring": true, "plagiarism_detection": true}'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_catalog_items"
        ordering = ["vendor", "name"]

    def __str__(self):
        return f"{self.name} ({self.vendor.name})"


class AssessmentOrder(models.Model):
    """An assessment sent to a specific candidate for a specific application."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("invited", "Invited"),
        ("started", "Started"),
        ("completed", "Completed"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="assessment_orders")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="assessment_orders"
    )
    catalog_item = models.ForeignKey(
        AssessmentCatalogItem, on_delete=models.PROTECT, related_name="orders"
    )
    ordered_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="assessment_orders_placed"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    external_order_id = models.CharField(max_length=255, blank=True, default="")
    invite_url = models.URLField(blank=True, default="")
    invited_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    # Anti-cheating flags returned by vendor
    anti_cheating_flags = models.JSONField(
        default=list, blank=True,
        help_text='[{"flag": "tab_switch", "count": 3, "severity": "medium"}]'
    )
    anti_cheating_cleared = models.BooleanField(
        null=True, blank=True,
        help_text="Human reviewer cleared anti-cheating flags"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["application"]),
        ]

    def __str__(self):
        return f"{self.catalog_item.name} — {self.application_id} ({self.status})"


class AssessmentResult(models.Model):
    """Scored result returned by a vendor for an assessment order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="assessment_results")
    order = models.OneToOneField(AssessmentOrder, on_delete=models.CASCADE, related_name="result")
    raw_score = models.FloatField(null=True, blank=True)
    normalized_score = models.FloatField(
        null=True, blank=True,
        help_text="Score normalized per catalog item's normalization_method"
    )
    percentile = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    band_label = models.CharField(max_length=100, blank=True, default="", help_text="e.g. Expert, Proficient")
    sub_scores = models.JSONField(
        default=dict, blank=True,
        help_text='{"problem_solving": 85, "code_quality": 72}'
    )
    report_url = models.URLField(blank=True, default="")
    ai_summary = models.TextField(blank=True, default="", help_text="AI-generated plain-language summary")
    explainability_payload = models.JSONField(
        default=dict, blank=True,
        help_text="Structured explanation of how score was derived (for audits/appeals)"
    )
    human_reviewed = models.BooleanField(
        default=False, help_text="EU AI Act — human has reviewed AI output"
    )
    human_reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_assessment_results"
    )
    human_review_note = models.TextField(blank=True, default="")
    human_override = models.BooleanField(null=True, blank=True, help_text="Reviewer overrode AI pass/fail")
    received_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_results"

    def __str__(self):
        return f"Result for order {self.order_id}"


class AssessmentWaiver(models.Model):
    """Records when an assessment is waived for a candidate (with reason)."""

    REASON_CHOICES = [
        ("accommodation", "Disability Accommodation"),
        ("strong_referral", "Strong Referral"),
        ("repeat_candidate", "Repeat / Known Candidate"),
        ("exec_override", "Executive Override"),
        ("portfolio_substitution", "Portfolio Substitution"),
        ("prior_certification", "Prior Certification on File"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="assessment_waivers")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="assessment_waivers"
    )
    catalog_item = models.ForeignKey(
        AssessmentCatalogItem, on_delete=models.PROTECT, related_name="waivers"
    )
    waived_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="granted_waivers"
    )
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assessment_waivers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Waiver: {self.catalog_item.name} for application {self.application_id}"


class AlternateAssessmentPath(models.Model):
    """An alternative assessment offered as a reasonable accommodation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="alternate_assessment_paths")
    original_catalog_item = models.ForeignKey(
        AssessmentCatalogItem, on_delete=models.CASCADE, related_name="alternate_paths"
    )
    alternate_catalog_item = models.ForeignKey(
        AssessmentCatalogItem, on_delete=models.CASCADE, related_name="used_as_alternate_for"
    )
    accommodation_type = models.CharField(
        max_length=100, blank=True, default="",
        help_text="e.g. Extended time, Screen reader compatible"
    )
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alternate_assessment_paths"

    def __str__(self):
        return f"{self.original_catalog_item.name} → {self.alternate_catalog_item.name}"


# ── NEW: Pre-screen Questionnaires ────────────────────────────────────────────

class ScreeningQuestionnaire(models.Model):
    """A reusable pre-screen questionnaire template."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screening_questionnaires")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    # If true, requires blind mode enforcement
    blind_review_enforced = models.BooleanField(
        default=False,
        help_text="Strip PII from reviewer view during screen review"
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="created_questionnaires"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "screening_questionnaires"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ScreeningQuestion(models.Model):
    """A single question within a screening questionnaire."""

    QUESTION_TYPE_CHOICES = [
        ("yes_no", "Yes / No"),
        ("multiple_choice", "Multiple Choice"),
        ("single_choice", "Single Choice"),
        ("short_text", "Short Text"),
        ("long_text", "Long Text"),
        ("numeric", "Numeric"),
        ("date", "Date"),
        ("file_upload", "File Upload"),
        ("async_audio", "Async Audio Response"),
        ("async_video", "Async Video Response"),
        ("rating_scale", "Rating Scale"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire = models.ForeignKey(
        ScreeningQuestionnaire, on_delete=models.CASCADE, related_name="questions"
    )
    order = models.PositiveIntegerField(default=0)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default="yes_no")
    options = models.JSONField(
        default=list, blank=True,
        help_text='For choice types: [{"value": "yes", "label": "Yes"}, ...]'
    )
    is_required = models.BooleanField(default=True)
    # Knockout logic
    is_knockout = models.BooleanField(
        default=False,
        help_text="If candidate answers disqualifying value, application is auto-rejected"
    )
    knockout_disqualifying_values = models.JSONField(
        default=list, blank=True,
        help_text='["no"] — values that trigger knockout disqualification'
    )
    knockout_reason_code = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Links to ScreeningDisqualificationReason.code"
    )
    # Weighted scoring
    weight = models.FloatField(
        default=0.0,
        help_text="Weight of this question in overall screening score (0–100)"
    )
    ideal_answer = models.JSONField(
        default=None, null=True, blank=True,
        help_text="Answer value(s) that score full weight points"
    )
    scoring_rubric = models.JSONField(
        default=dict, blank=True,
        help_text='{"value": score} map for partial credit'
    )
    help_text_for_candidate = models.TextField(blank=True, default="")

    class Meta:
        db_table = "screening_questions"
        ordering = ["questionnaire", "order"]

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:60]}"


class ScreeningQuestionnaireResponse(models.Model):
    """A candidate's completed response to a questionnaire for an application."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="questionnaire_responses")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="screening_responses"
    )
    questionnaire = models.ForeignKey(
        ScreeningQuestionnaire, on_delete=models.PROTECT, related_name="responses"
    )
    answers = models.JSONField(
        default=dict,
        help_text='{"<question_id>": <answer_value>}'
    )
    computed_score = models.FloatField(
        null=True, blank=True,
        help_text="Weighted total score after applying question weights/rubrics"
    )
    knockout_triggered = models.BooleanField(default=False)
    knockout_question = models.ForeignKey(
        ScreeningQuestion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="triggered_knockouts"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "screening_questionnaire_responses"
        unique_together = [("application", "questionnaire")]

    def __str__(self):
        return f"Response: {self.questionnaire} / {self.application_id}"


# ── NEW: Screening Rules Engine ───────────────────────────────────────────────

class ScreeningRuleSet(models.Model):
    """A named set of weighted screening rules attached to a job."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screening_rule_sets")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    # FK to Job (nullable — can be a reusable template)
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="screening_rule_sets"
    )
    is_template = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # Score threshold to auto-advance
    auto_advance_threshold = models.FloatField(
        null=True, blank=True,
        help_text="Candidates scoring ≥ this weighted total are auto-advanced"
    )
    # Score threshold to auto-reject
    auto_reject_threshold = models.FloatField(
        null=True, blank=True,
        help_text="Candidates scoring < this weighted total are auto-rejected"
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="created_rule_sets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "screening_rule_sets"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ScreeningRule(models.Model):
    """A single weighted rule within a ScreeningRuleSet."""

    RULE_TYPE_CHOICES = [
        ("must_have", "Must-Have Requirement"),
        ("preferred", "Preferred Requirement"),
        ("nice_to_have", "Nice-to-Have"),
        ("disqualifier", "Disqualifier"),
        ("credential", "Credential / License"),
        ("experience_years", "Years of Experience"),
        ("education", "Education Level"),
        ("skill", "Skill Match"),
        ("location", "Location / Commute"),
        ("availability", "Availability / Start Date"),
        ("salary", "Salary Expectation"),
        ("questionnaire_score", "Questionnaire Score"),
        ("assessment_score", "Assessment Score"),
        ("custom", "Custom Logic"),
    ]

    OPERATOR_CHOICES = [
        ("eq", "Equals"),
        ("neq", "Not Equals"),
        ("gte", "Greater Than or Equal"),
        ("lte", "Less Than or Equal"),
        ("contains", "Contains"),
        ("not_contains", "Does Not Contain"),
        ("in", "In List"),
        ("not_in", "Not In List"),
        ("exists", "Exists / Present"),
        ("not_exists", "Not Present"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_set = models.ForeignKey(ScreeningRuleSet, on_delete=models.CASCADE, related_name="rules")
    order = models.PositiveIntegerField(default=0)
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES)
    field_path = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Dot-path into candidate/application data: e.g. 'years_experience', 'skills'"
    )
    operator = models.CharField(max_length=20, choices=OPERATOR_CHOICES, default="eq")
    expected_value = models.JSONField(
        default=None, null=True, blank=True,
        help_text="Value to compare against"
    )
    weight = models.FloatField(
        default=1.0,
        help_text="Weight in overall score when rule passes (0–100)"
    )
    is_knockout = models.BooleanField(
        default=False,
        help_text="Failure immediately disqualifies candidate"
    )
    knockout_reason_code = models.CharField(
        max_length=100, blank=True, default=""
    )
    description = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "screening_rules"
        ordering = ["rule_set", "order"]

    def __str__(self):
        return f"{self.rule_set.name} / {self.rule_type}: {self.field_path} {self.operator}"


class ScreeningRuleEvaluation(models.Model):
    """Result of running a ScreeningRuleSet against one application."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screening_rule_evaluations")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="rule_evaluations"
    )
    rule_set = models.ForeignKey(
        ScreeningRuleSet, on_delete=models.PROTECT, related_name="evaluations"
    )
    total_score = models.FloatField(default=0.0)
    max_possible_score = models.FloatField(default=0.0)
    passed_rules = models.JSONField(default=list, blank=True)
    failed_rules = models.JSONField(default=list, blank=True)
    knockout_rule = models.ForeignKey(
        ScreeningRule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="triggered_evaluations"
    )
    auto_decision = models.CharField(
        max_length=20, blank=True, default="",
        help_text="advance | reject | review — set by rule engine"
    )
    # Explainability
    explanation_payload = models.JSONField(
        default=dict, blank=True,
        help_text="Structured explanation: which rules passed/failed and why"
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "screening_rule_evaluations"
        ordering = ["-evaluated_at"]
        indexes = [models.Index(fields=["application"])]

    def __str__(self):
        return f"RuleEval: {self.rule_set} / {self.application_id} → {self.auto_decision}"


# ── NEW: Credential / License Verification ────────────────────────────────────

class CredentialVerification(models.Model):
    """Tracks verification of a candidate credential or license."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("verified", "Verified"),
        ("failed", "Failed / Not Verified"),
        ("expired", "Credential Expired"),
        ("waived", "Waived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="credential_verifications")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="credential_verifications"
    )
    credential_type = models.CharField(
        max_length=255,
        help_text="e.g. CPA, AWS Solutions Architect, State Bar License, RN License"
    )
    credential_number = models.CharField(max_length=255, blank=True, default="")
    issuing_authority = models.CharField(max_length=255, blank=True, default="")
    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verification_method = models.CharField(
        max_length=50, blank=True, default="",
        help_text="manual | vendor_api | primary_source"
    )
    vendor_reference_id = models.CharField(max_length=255, blank=True, default="")
    verified_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="credential_verifications_performed"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    document_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "credential_verifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.credential_type} — {self.status} ({self.application_id})"


# ── NEW: Screen Decision Taxonomy ─────────────────────────────────────────────

class ScreeningDecisionReason(models.Model):
    """Tenant-configurable taxonomy of screen pass/fail/hold reasons."""

    CATEGORY_CHOICES = [
        ("pass", "Pass / Advance"),
        ("hold", "Hold for Review"),
        ("reject", "Reject / Disqualify"),
        ("appeal", "Under Appeal"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screening_decision_reasons")
    code = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, default="")
    # Compliance flags
    requires_documentation = models.BooleanField(default=False)
    is_protected_class_sensitive = models.BooleanField(
        default=False,
        help_text="Reason may trigger bias review; requires extra audit logging"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "screening_decision_reasons"
        ordering = ["category", "label"]
        unique_together = [("tenant", "code")]

    def __str__(self):
        return f"[{self.category}] {self.label}"


class ScreeningDecision(models.Model):
    """A formal screening decision recorded for an application."""

    DECISION_CHOICES = [
        ("advance", "Advance"),
        ("hold", "Hold"),
        ("reject", "Reject"),
        ("waive_assessment", "Waive Assessment"),
        ("request_more_info", "Request More Info"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screening_decisions")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="screening_decisions"
    )
    decision = models.CharField(max_length=30, choices=DECISION_CHOICES)
    reason = models.ForeignKey(
        ScreeningDecisionReason, on_delete=models.PROTECT, related_name="decisions"
    )
    rule_evaluation = models.ForeignKey(
        ScreeningRuleEvaluation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="decisions"
    )
    decided_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="screening_decisions_made"
    )
    is_automated = models.BooleanField(
        default=False,
        help_text="True if decision was made by rule engine without human"
    )
    notes = models.TextField(blank=True, default="")
    # Blind review — store whether PII was visible to reviewer at decision time
    blind_review_active = models.BooleanField(default=False)
    # Explainability link
    explanation_summary = models.TextField(
        blank=True, default="",
        help_text="Plain-language explanation of why this decision was reached"
    )
    decided_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "screening_decisions"
        ordering = ["-decided_at"]
        indexes = [models.Index(fields=["application"])]

    def __str__(self):
        return f"{self.decision} — {self.application_id}"


# ── NEW: Screen Review Queue ──────────────────────────────────────────────────

class ScreenReviewQueue(models.Model):
    """Queue entry for applications awaiting human screen review."""

    PRIORITY_CHOICES = [
        ("urgent", "Urgent"),
        ("high", "High"),
        ("normal", "Normal"),
        ("low", "Low"),
    ]

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("assigned", "Assigned"),
        ("in_review", "In Review"),
        ("completed", "Completed"),
        ("escalated", "Escalated"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screen_review_queue")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="screen_queue_entries"
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="queued")
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_screen_reviews"
    )
    # Blind review mode
    blind_review_mode = models.BooleanField(
        default=False,
        help_text="When true, reviewer UI strips candidate PII (name, photo, gender, age indicators)"
    )
    due_by = models.DateTimeField(null=True, blank=True)
    review_started_at = models.DateTimeField(null=True, blank=True)
    review_completed_at = models.DateTimeField(null=True, blank=True)
    queue_reason = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Why this application is in the queue (auto-populated)"
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "screen_review_queue"
        ordering = ["priority", "created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self):
        return f"Queue: {self.application_id} [{self.priority}] {self.status}"


# ── NEW: Screening Audit Trail ────────────────────────────────────────────────

class ScreeningAuditEntry(models.Model):
    """Immutable audit log entry for any screening action."""

    ACTION_CHOICES = [
        ("questionnaire_submitted", "Questionnaire Submitted"),
        ("knockout_triggered", "Knockout Triggered"),
        ("rule_evaluation_run", "Rule Evaluation Run"),
        ("auto_decision_made", "Auto Decision Made"),
        ("human_decision_made", "Human Decision Made"),
        ("blind_review_toggled", "Blind Review Toggled"),
        ("queue_assigned", "Review Queue Assigned"),
        ("queue_escalated", "Review Queue Escalated"),
        ("assessment_ordered", "Assessment Ordered"),
        ("assessment_completed", "Assessment Completed"),
        ("result_normalized", "Result Normalized"),
        ("anti_cheat_flag_raised", "Anti-Cheat Flag Raised"),
        ("anti_cheat_cleared", "Anti-Cheat Flag Cleared"),
        ("credential_verified", "Credential Verified"),
        ("waiver_granted", "Waiver Granted"),
        ("alternate_path_assigned", "Alternate Path Assigned"),
        ("appeal_submitted", "Appeal Submitted"),
        ("appeal_reviewed", "Appeal Reviewed"),
        ("explanation_generated", "Explanation Generated"),
        ("decision_overridden", "Decision Overridden"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screening_audit_entries")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="screening_audit_entries"
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="screening_audit_actions"
    )
    actor_label = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Captured display name at time of action (survives user deletion)"
    )
    is_system_action = models.BooleanField(default=False)
    payload = models.JSONField(
        default=dict, blank=True,
        help_text="Snapshot of relevant data at time of action"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "screening_audit_entries"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["application"]),
            models.Index(fields=["tenant", "action"]),
        ]

    def __str__(self):
        return f"[{self.action}] app={self.application_id} at {self.occurred_at}"


# ── NEW: Candidate Appeals & Reconsideration ──────────────────────────────────

class ScreeningAppeal(models.Model):
    """A candidate's formal appeal of a screening decision."""

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("upheld", "Upheld — Decision Unchanged"),
        ("overturned", "Overturned — Decision Reversed"),
        ("withdrawn", "Withdrawn by Candidate"),
        ("closed", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="screening_appeals")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="screening_appeals"
    )
    original_decision = models.ForeignKey(
        ScreeningDecision, on_delete=models.PROTECT, related_name="appeals"
    )
    candidate_statement = models.TextField(
        help_text="Candidate's explanation/grounds for appeal"
    )
    supporting_evidence_urls = models.JSONField(
        default=list, blank=True,
        help_text="URLs to uploaded supporting documents"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    assigned_reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_appeals"
    )
    reviewer_notes = models.TextField(blank=True, default="")
    outcome_explanation = models.TextField(
        blank=True, default="",
        help_text="Plain-language explanation of appeal outcome sent to candidate"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "screening_appeals"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Appeal: {self.application_id} [{self.status}]"


# ── NEW: Explainable Match Snapshot ───────────────────────────────────────────

class ExplainableMatchSnapshot(models.Model):
    """Stores a versioned, auditable explanation of match/screening logic output."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="match_snapshots")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="match_snapshots"
    )
    # Scores
    overall_match_score = models.FloatField(null=True, blank=True)
    screening_score = models.FloatField(null=True, blank=True)
    assessment_score = models.FloatField(null=True, blank=True)
    questionnaire_score = models.FloatField(null=True, blank=True)
    # Breakdown
    score_breakdown = models.JSONField(
        default=dict, blank=True,
        help_text="Component scores: skills, experience, education, location, etc."
    )
    must_have_checks = models.JSONField(
        default=list, blank=True,
        help_text='[{"requirement": "5+ years Python", "met": true, "evidence": "..."}]'
    )
    disqualifiers_triggered = models.JSONField(
        default=list, blank=True
    )
    # Human-readable explanation
    plain_language_summary = models.TextField(blank=True, default="")
    # Model/version metadata
    engine_version = models.CharField(max_length=50, blank=True, default="")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "explainable_match_snapshots"
        ordering = ["-generated_at"]
        indexes = [models.Index(fields=["application"])]

    def __str__(self):
        return f"MatchSnapshot: {self.application_id} score={self.overall_match_score}"
