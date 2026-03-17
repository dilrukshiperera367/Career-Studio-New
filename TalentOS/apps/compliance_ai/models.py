"""Compliance AI app — EU AI Act Annex III compliance: prompt logs, human review, bias monitoring, DPIA."""

import uuid
from django.db import models


class AIModel(models.Model):
    """Registry of AI/ML models used within TalentOS."""

    RISK_LEVEL_CHOICES = [
        ("minimal", "Minimal Risk"),
        ("limited", "Limited Risk"),
        ("high", "High Risk (Annex III)"),
        ("unacceptable", "Unacceptable Risk (Prohibited)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="ai_models")
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    provider = models.CharField(max_length=255, blank=True, default="")
    use_case = models.CharField(max_length=255, help_text="e.g. Resume scoring, JD quality analysis")
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default="limited")
    is_active = models.BooleanField(default=True)
    technical_documentation_url = models.URLField(blank=True, default="")
    conformity_assessment_done = models.BooleanField(default=False)
    human_oversight_required = models.BooleanField(
        default=True, help_text="EU AI Act Annex III — mandatory for high-risk"
    )
    explainability_method = models.CharField(
        max_length=100, blank=True, default="",
        help_text="e.g. SHAP, LIME, rule-based explanation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_models"
        ordering = ["name", "-created_at"]

    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_risk_level_display()})"


class AIPromptLog(models.Model):
    """Logs every prompt sent to an AI model for auditability."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="ai_prompt_logs")
    ai_model = models.ForeignKey(AIModel, on_delete=models.PROTECT, related_name="prompt_logs")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_prompts"
    )
    prompt_hash = models.CharField(max_length=64, help_text="SHA-256 of prompt text for dedup")
    prompt_preview = models.CharField(
        max_length=500, blank=True, default="",
        help_text="First 500 chars of prompt (no PII)"
    )
    input_tokens = models.IntegerField(null=True, blank=True)
    latency_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_prompt_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "ai_model"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Prompt to {self.ai_model.name} at {self.created_at}"


class AIOutputLog(models.Model):
    """Logs every output from an AI model for auditability and bias review."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="ai_output_logs")
    prompt_log = models.OneToOneField(AIPromptLog, on_delete=models.CASCADE, related_name="output_log")
    output_summary = models.TextField(blank=True, default="", help_text="Plain-language summary (no PII)")
    score_or_decision = models.CharField(max_length=255, blank=True, default="")
    explanation = models.TextField(blank=True, default="", help_text="SHAP/LIME or rule explanation")
    output_tokens = models.IntegerField(null=True, blank=True)
    flagged_for_review = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_output_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Output for prompt {self.prompt_log_id}"


class HumanReviewQueue(models.Model):
    """Queue of AI outputs requiring human review (EU AI Act Annex III)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_review", "In Review"),
        ("approved", "Approved"),
        ("overridden", "Overridden"),
        ("escalated", "Escalated"),
    ]

    OBJECT_TYPE_CHOICES = [
        ("application_score", "Application Score"),
        ("resume_parse", "Resume Parse"),
        ("jd_quality", "JD Quality Score"),
        ("assessment_result", "Assessment Result"),
        ("offer_recommendation", "Offer Recommendation"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="human_review_queue")
    output_log = models.ForeignKey(
        AIOutputLog, on_delete=models.CASCADE, related_name="review_queue_items"
    )
    object_type = models.CharField(max_length=30, choices=OBJECT_TYPE_CHOICES)
    object_id = models.UUIDField(help_text="UUID of the reviewed object (application, score, etc.)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_reviews_assigned"
    )
    review_deadline = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "human_review_queue"
        ordering = ["review_deadline", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self):
        return f"Review: {self.object_type} {self.object_id} ({self.status})"


class AIOverrideRecord(models.Model):
    """Records when a human overrides an AI decision — mandatory for EU AI Act audit trail."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="ai_override_records")
    review_item = models.OneToOneField(
        HumanReviewQueue, on_delete=models.CASCADE, related_name="override_record"
    )
    ai_decision = models.CharField(max_length=255, help_text="Original AI output / decision")
    human_decision = models.CharField(max_length=255, help_text="Human's final decision")
    override_reason = models.TextField()
    override_category = models.CharField(
        max_length=100, blank=True, default="",
        help_text="e.g. bias_suspected, factual_error, context_not_captured"
    )
    overridden_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="ai_overrides"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_override_records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Override by {self.overridden_by_id} on {self.created_at.date()}"


class BiasMonitoringReport(models.Model):
    """Periodic statistical bias / disparate impact report for an AI model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="bias_monitoring_reports")
    ai_model = models.ForeignKey(AIModel, on_delete=models.PROTECT, related_name="bias_reports")
    period_start = models.DateField()
    period_end = models.DateField()
    total_decisions = models.IntegerField(default=0)
    adverse_impact_ratio = models.JSONField(
        default=dict, blank=True,
        help_text='{"gender": {"female": 0.82, "male": 1.0}, "ethnicity": {...}}'
    )
    disparate_impact_flags = models.JSONField(
        default=list, blank=True,
        help_text="Groups with ratio < 0.8 (4/5ths rule)"
    )
    remediation_actions = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bias_reports_reviewed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bias_monitoring_reports"
        ordering = ["-period_start"]

    def __str__(self):
        return f"Bias report: {self.ai_model.name} {self.period_start}–{self.period_end}"


class DPIATemplate(models.Model):
    """A Data Protection Impact Assessment template (GDPR Art. 35)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="dpia_templates")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    sections = models.JSONField(
        default=list, blank=True,
        help_text='[{"title": "...", "questions": ["..."]}]'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dpia_templates"

    def __str__(self):
        return f"DPIA Template: {self.name}"


class DPIAAssessment(models.Model):
    """A completed DPIA for a specific AI model or processing activity."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="dpia_assessments")
    template = models.ForeignKey(DPIATemplate, on_delete=models.PROTECT, related_name="assessments")
    ai_model = models.ForeignKey(
        AIModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="dpia_assessments"
    )
    title = models.CharField(max_length=255)
    answers = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    dpo_reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dpia_reviews"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True, help_text="Next scheduled review")
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="dpias_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dpia_assessments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DPIA: {self.title} ({self.status})"


class AIPolicy(models.Model):
    """Tenant-level policies governing AI feature usage (opt-ins, restrictions)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="ai_policy")
    allow_resume_scoring = models.BooleanField(default=True)
    allow_jd_analysis = models.BooleanField(default=True)
    allow_market_benchmarking = models.BooleanField(default=True)
    allow_predictive_analytics = models.BooleanField(default=True)
    require_human_review_for_rejections = models.BooleanField(
        default=True, help_text="Require human confirmation before auto-rejecting via AI"
    )
    data_retention_days = models.IntegerField(
        default=365, help_text="Days AI logs are retained before purging"
    )
    custom_restrictions = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="ai_policy_updates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_policies"

    def __str__(self):
        return f"AI Policy — {self.tenant.name}"


class CandidateAppeal(models.Model):
    """A candidate's appeal against an AI-influenced hiring decision."""

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("upheld", "Upheld"),
        ("dismissed", "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_appeals")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="appeals"
    )
    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="compliance_appeals"
    )
    appeal_reason = models.TextField()
    ai_decision_explained = models.TextField(
        blank=True, default="",
        help_text="Explanation of the AI decision that is being appealed"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="candidate_appeal_reviews"
    )
    outcome_notes = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_appeals"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Appeal by {self.candidate_id} ({self.status})"
