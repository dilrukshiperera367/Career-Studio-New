"""
Redeployment app models.
Ending-assignment alerts, redeployment pools, bench management,
availability tracking, role-match suggestions, conversion analytics.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class RedeploymentPool(models.Model):
    """
    A managed pool of contractors available for redeployment.
    Can be segmented by skill, geography, sector, or pay tier.
    """

    class PoolType(models.TextChoices):
        GENERAL = "general", "General Available Pool"
        SKILL_BASED = "skill_based", "Skill-Based"
        SECTOR = "sector", "Sector-Specific"
        GEOGRAPHY = "geography", "Geography-Based"
        CLIENT_SPECIFIC = "client_specific", "Client-Specific Bench"
        SILVER_MEDALIST = "silver_medalist", "Silver Medalist Pool"
        BOOMERANG = "boomerang", "Boomerang Alumni"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="redeployment_pools"
    )
    name = models.CharField(max_length=200)
    pool_type = models.CharField(
        max_length=30, choices=PoolType.choices, default=PoolType.GENERAL
    )
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list)
    target_skills = models.JSONField(default=list)
    target_geographies = models.JSONField(default=list)
    managed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_pools"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "redep_pool"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_pool_type_display()})"


class RedeploymentPoolMember(models.Model):
    """A candidate in a redeployment pool."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Available"
        PLACED = "placed", "Placed / No Longer Available"
        OPTED_OUT = "opted_out", "Opted Out"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(
        RedeploymentPool, on_delete=models.CASCADE, related_name="members"
    )
    candidate = models.ForeignKey(
        "submissions.CandidateProfile", on_delete=models.CASCADE, related_name="pool_memberships"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    available_from = models.DateField(null=True, blank=True)
    redeployment_score = models.IntegerField(null=True, blank=True)  # 0-100
    added_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="pool_additions"
    )
    notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "redep_pool_member"
        unique_together = [["pool", "candidate"]]

    def __str__(self):
        return f"{self.candidate} in {self.pool.name}"


class EndingAssignmentAlert(models.Model):
    """
    Alert generated when an assignment is ending within a threshold.
    Triggers recruiter re-engagement workflow.
    """

    class AlertStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        EXTENDED = "extended", "Assignment Extended"
        REDEPLOYED = "redeployed", "Redeployed"
        ENDED = "ended", "Assignment Ended (No Redeploy)"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="ending_alerts"
    )
    assignment = models.ForeignKey(
        "contractor_ops.Assignment", on_delete=models.CASCADE, related_name="ending_alerts"
    )
    alert_status = models.CharField(
        max_length=20, choices=AlertStatus.choices, default=AlertStatus.OPEN
    )
    assignment_end_date = models.DateField()
    days_until_end = models.IntegerField()
    assigned_to = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="redeployment_alerts"
    )
    action_taken = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "redep_ending_alert"
        ordering = ["assignment_end_date"]

    def __str__(self):
        return f"Alert: {self.assignment} ending {self.assignment_end_date}"


class RedeploymentOpportunity(models.Model):
    """
    A matched job order suggested for a redeployable contractor.
    Created by the redeployment engine.
    """

    class MatchStatus(models.TextChoices):
        SUGGESTED = "suggested", "AI Suggested"
        REVIEWED = "reviewed", "Recruiter Reviewed"
        PURSUING = "pursuing", "Pursuing"
        SUBMITTED = "submitted", "Submitted"
        PLACED = "placed", "Placed"
        REJECTED = "rejected", "Not a Fit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="redeployment_opportunities"
    )
    candidate = models.ForeignKey(
        "submissions.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="redeployment_opportunities",
    )
    job_order = models.ForeignKey(
        "job_orders.JobOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="redeployment_opportunities",
    )
    match_score = models.IntegerField(null=True, blank=True)
    match_reasons = models.JSONField(default=list)
    match_status = models.CharField(
        max_length=20, choices=MatchStatus.choices, default=MatchStatus.SUGGESTED
    )
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_redeploy"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "redep_opportunity"
        ordering = ["-match_score"]

    def __str__(self):
        return f"Redeploy: {self.candidate} → {self.job_order} ({self.match_score}%)"
