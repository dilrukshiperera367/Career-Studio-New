"""AI Governance — decision logs, bias metrics, guardrails."""
import uuid
from django.db import models
from django.conf import settings


class AIDecisionLog(models.Model):
    """Every AI-assisted decision with full I/O for audit trail."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    decision_type = models.CharField(max_length=50)  # e.g. Job Matching, Resume Screen
    action = models.CharField(max_length=200)
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ai_decisions"
    )
    candidate_name = models.CharField(max_length=200, blank=True, default="")
    job_title = models.CharField(max_length=200, blank=True, default="")
    match_score = models.IntegerField(null=True, blank=True)
    inputs = models.TextField(blank=True, default="")
    output = models.TextField(blank=True, default="")
    is_reviewed = models.BooleanField(default=False)
    reviewer = models.CharField(max_length=200, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_ai_decision_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.decision_type}: {self.action}"


class BiasMetric(models.Model):
    """Periodic bias measurement across demographic dimensions."""

    class MetricStatus(models.TextChoices):
        PASS = "pass", "Pass"
        WARNING = "warning", "Warning"
        FAIL = "fail", "Fail"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.CharField(max_length=50)  # Gender, Age, Location, Education
    metric_name = models.CharField(max_length=200)
    value = models.CharField(max_length=100)
    threshold = models.CharField(max_length=50, blank=True, default=">0.80")
    status = models.CharField(
        max_length=10, choices=MetricStatus.choices, default=MetricStatus.PASS
    )
    measured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_bias_metrics"
        ordering = ["-measured_at"]


class Guardrail(models.Model):
    """Active AI guardrail configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    category = models.CharField(max_length=50, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_guardrails"
        ordering = ["name"]

    def __str__(self):
        return self.name
