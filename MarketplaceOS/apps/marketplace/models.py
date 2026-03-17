"""
MarketplaceOS — apps.marketplace

Core discovery and matching engine.

Models:
    SavedProvider           — Buyer's saved/shortlisted providers
    SavedService            — Buyer's saved services
    ProviderComparison      — Buyer's side-by-side comparison list
    MatchRequest            — Buyer's matching request (AI-assisted)
    MatchRecommendation     — Individual match recommendation from a request
    RecommendationFeedback  — Buyer feedback on a recommendation
    BuyerProfile            — Extended buyer profile for matching
"""
import uuid
from django.db import models
from django.conf import settings


class SavedProvider(models.Model):
    """Buyer bookmarks a provider for later."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_providers",
    )
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="saved_by",
    )
    notes = models.CharField(max_length=500, blank=True, default="")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_saved_provider"
        unique_together = [["buyer", "provider"]]
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.buyer} saved {self.provider}"


class SavedService(models.Model):
    """Buyer bookmarks a specific service."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_services",
    )
    service = models.ForeignKey(
        "services_catalog.Service", on_delete=models.CASCADE, related_name="saved_by",
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_saved_service"
        unique_together = [["buyer", "service"]]
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.buyer} saved service {self.service}"


class ProviderComparison(models.Model):
    """
    Buyer's active comparison list (up to 4 providers).
    Each comparison is a named 'session' the buyer creates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comparisons",
    )
    label = models.CharField(max_length=200, blank=True, default="My Comparison")
    providers = models.ManyToManyField("providers.Provider", blank=True, related_name="comparisons")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_provider_comparison"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Comparison by {self.buyer}: {self.label}"


class BuyerProfile(models.Model):
    """
    Extended profile capturing buyer's goals and preferences —
    used for personalised matching and recommendations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buyer_profile",
    )
    current_role = models.CharField(max_length=200, blank=True, default="")
    target_role = models.CharField(max_length=200, blank=True, default="")
    industry = models.CharField(max_length=100, blank=True, default="")
    experience_years = models.IntegerField(null=True, blank=True)
    skills = models.JSONField(default=list)
    learning_goals = models.JSONField(default=list)
    preferred_provider_types = models.JSONField(default=list)
    budget_min_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_max_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preferred_delivery_mode = models.CharField(max_length=20, blank=True, default="",
                                                help_text="online/in_person/any")
    preferred_language = models.CharField(max_length=20, blank=True, default="")
    timezone = models.CharField(max_length=50, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_buyer_profile"

    def __str__(self):
        return f"BuyerProfile for {self.buyer}"


class MatchRequest(models.Model):
    """
    Buyer submits a structured request for provider matching.
    The platform (or AI agent) generates MatchRecommendations.
    """

    class MatchStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="match_requests",
    )
    provider_type = models.CharField(max_length=50, blank=True, default="")
    service_type = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(help_text="Freeform description of what the buyer needs.")
    goals = models.JSONField(default=list)
    budget_max_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preferred_dates = models.JSONField(default=list, help_text="ISO date strings of preferred session dates.")
    delivery_mode = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(max_length=12, choices=MatchStatus.choices, default=MatchStatus.PENDING)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_match_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"MatchRequest by {self.buyer} — {self.status}"


class MatchRecommendation(models.Model):
    """A single provider recommended in response to a MatchRequest."""

    class RecommendationSource(models.TextChoices):
        ALGORITHM = "algorithm", "Matching Algorithm"
        AI = "ai", "AI Engine"
        MANUAL = "manual", "Manual (Admin)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match_request = models.ForeignKey(MatchRequest, on_delete=models.CASCADE, related_name="recommendations")
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="match_recommendations",
    )
    rank = models.IntegerField(default=1)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                       help_text="0–100 match score.")
    match_reasons = models.JSONField(default=list, help_text="['availability', 'skill_overlap', ...]")
    source = models.CharField(max_length=12, choices=RecommendationSource.choices, default=RecommendationSource.ALGORITHM)
    was_viewed = models.BooleanField(default=False)
    was_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_match_recommendation"
        ordering = ["rank"]

    def __str__(self):
        return f"Recommendation #{self.rank}: {self.provider} for request {self.match_request_id}"


class RecommendationFeedback(models.Model):
    """Buyer rates the quality of a recommendation."""

    class FeedbackType(models.TextChoices):
        BOOKED = "booked", "Booked this provider"
        NOT_RELEVANT = "not_relevant", "Not relevant"
        TOO_EXPENSIVE = "too_expensive", "Too expensive"
        NO_AVAILABILITY = "no_availability", "No availability match"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recommendation = models.OneToOneField(
        MatchRecommendation, on_delete=models.CASCADE, related_name="feedback",
    )
    feedback_type = models.CharField(max_length=20, choices=FeedbackType.choices)
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_recommendation_feedback"

    def __str__(self):
        return f"Feedback on recommendation {self.recommendation_id}: {self.feedback_type}"
