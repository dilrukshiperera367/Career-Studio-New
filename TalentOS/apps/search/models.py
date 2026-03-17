"""Search app — Saved searches, score history, and search configuration."""

import uuid
from django.db import models


class SavedSearch(models.Model):
    """A saved search query for re-use and alert notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="saved_searches")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="saved_searches")
    name = models.CharField(max_length=255)
    query_json = models.JSONField(default=dict,
        help_text='{"query": "python", "location": "NYC", "min_experience": 3, "skills": ["React"]}')
    notify_on_match = models.BooleanField(default=False,
        help_text="Email user when new candidates match this search")
    last_run_at = models.DateTimeField(null=True, blank=True)
    result_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_searches"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"


class ScoreHistory(models.Model):
    """Tracks how a candidate's score changes over time per job."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, related_name="score_history")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, null=True, blank=True, related_name="score_history")
    score = models.FloatField()
    breakdown = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=100, blank=True, default="",
        help_text="initial_score, re_scored, skills_updated, resume_updated")
    scored_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "score_history"
        ordering = ["-scored_at"]
        indexes = [
            models.Index(fields=["tenant", "candidate", "scored_at"]),
        ]

    def __str__(self):
        return f"Score {self.score} for {self.candidate_id} at {self.scored_at}"


class SkillSynonym(models.Model):
    """Maps variant skill names to canonical names — React.js = ReactJS = React."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, null=True, blank=True,
        help_text="null = global synonym")
    variant = models.CharField(max_length=200, db_index=True)
    canonical = models.CharField(max_length=200)

    class Meta:
        db_table = "skill_synonyms"
        unique_together = [("tenant", "variant")]

    def __str__(self):
        return f"{self.variant} → {self.canonical}"


class SearchSegmentAlert(models.Model):
    """
    Notifies a user when the estimated supply for a talent segment
    changes significantly (e.g. a skill pool shrinks below a threshold).
    Used by analytics_forecasting and sourcing teams.
    """

    ALERT_TYPE_CHOICES = [
        ("supply_drop", "Supply Drop"),
        ("supply_surge", "Supply Surge"),
        ("competition_spike", "Competition Spike"),
        ("new_match", "New Talent Match"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("triggered", "Triggered"),
        ("dismissed", "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="segment_alerts")
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="segment_alerts",
    )
    name = models.CharField(max_length=255)
    segment_query = models.JSONField(
        default=dict, blank=True,
        help_text='{"skills": [...], "location": "...", "min_experience": 3}'
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, default="supply_drop")
    threshold = models.FloatField(
        null=True, blank=True,
        help_text="Numeric threshold that triggers the alert (e.g. percentage change)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "search_segment_alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self):
        return f"SegmentAlert: {self.name} ({self.alert_type})"
