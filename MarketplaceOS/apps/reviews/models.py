"""
MarketplaceOS — apps.reviews

Reviews, Ratings & Proof — deeply verified and authentic.

Models:
    Review           — Verified post-booking review with multi-dimension ratings
    ReviewFlag       — Flag a review as suspicious / policy violation
    ProviderResponse — Provider's public reply to a review
    OutcomeTag       — Platform-defined structured outcome tags
    ReviewSummary    — Denormalized review stats per provider (updated via signal)

FTC Compliance:
    All reviews are "verified booking reviews" tied to a completed booking.
    No incentivised reviews. Authenticity flags built in per FTC 16 CFR 465 (Oct 2024).
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class OutcomeTag(models.Model):
    """Platform-defined outcome tags that reviewers can select."""
    slug = models.SlugField(max_length=60, primary_key=True)
    label = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, default="",
                                 help_text="e.g. interview_prep, resume, career_switch")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mp_outcome_tag"
        ordering = ["label"]

    def __str__(self):
        return self.label


class Review(models.Model):
    """
    Verified post-booking review.

    Only buyers who completed a real booking can review. Reviews are hidden
    pending moderation on first submission. Provider responses are public.
    FTC-compliant: reviews are authenticated to verified transactions.
    """

    class ModerationStatus(models.TextChoices):
        PENDING = "pending", "Pending Moderation"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        FLAGGED = "flagged", "Flagged for Investigation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="review",
    )
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_given",
    )

    # Dimension ratings (1–5)
    rating_overall = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall star rating 1–5.",
    )
    rating_helpfulness = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    rating_clarity = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    rating_expertise = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    rating_punctuality = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    rating_value = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])

    # Written review
    headline = models.CharField(max_length=200, blank=True, default="")
    body = models.TextField(blank=True, default="")
    outcome_tags = models.ManyToManyField(OutcomeTag, blank=True, related_name="reviews")
    would_recommend = models.BooleanField(default=True)
    would_rebook = models.BooleanField(default=True)

    # Display
    is_anonymous = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False,
                                       help_text="Provider/admin can feature a testimonial.")

    # Moderation (FTC compliance built-in)
    moderation_status = models.CharField(
        max_length=10, choices=ModerationStatus.choices, default=ModerationStatus.PENDING,
    )
    moderation_notes = models.TextField(blank=True, default="")
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="moderated_reviews",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    # Authenticity signals
    authenticity_score = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                              help_text="ML-scored 0–100. Low = suspicious.")
    is_suspicious = models.BooleanField(default=False)
    authenticity_flags = models.JSONField(default=list,
                                           help_text="List of flag codes from fraud detector.")

    # Metrics
    helpful_votes = models.IntegerField(default=0)
    unhelpful_votes = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_review"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "moderation_status"]),
            models.Index(fields=["rating_overall"]),
        ]

    def __str__(self):
        return f"Review by {self.reviewer.email} — {self.rating_overall}* — {self.moderation_status}"


class ProviderResponse(models.Model):
    """Provider's public reply to a review."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="provider_response")
    body = models.TextField()
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_provider_response"

    def __str__(self):
        return f"Response to {self.review}"


class ReviewFlag(models.Model):
    """Flag a review as potentially suspicious or policy-violating."""

    class FlagReason(models.TextChoices):
        FAKE = "fake", "Suspected Fake Review"
        INCENTIVISED = "incentivised", "Likely Incentivised (FTC)"
        INAPPROPRIATE = "inappropriate", "Inappropriate Content"
        SPAM = "spam", "Spam"
        CONFLICT = "conflict", "Conflict of Interest"
        PERSONAL_INFO = "personal_info", "Contains Personal Information"
        OTHER = "other", "Other"

    class FlagStatus(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED_KEPT = "resolved_kept", "Resolved — Review Kept"
        RESOLVED_REMOVED = "resolved_removed", "Resolved — Review Removed"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="flags")
    flagged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=FlagReason.choices)
    details = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=FlagStatus.choices, default=FlagStatus.OPEN)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="resolved_review_flags",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_review_flag"
        unique_together = [["review", "flagged_by"]]

    def __str__(self):
        return f"Flag ({self.reason}) on {self.review}"


class ReviewSummary(models.Model):
    """
    Denormalized review aggregate per provider.
    Updated by signal on Review save/delete. Used to power fast provider listing.
    """
    provider = models.OneToOneField(
        "providers.Provider", on_delete=models.CASCADE, related_name="review_summary",
    )
    total_reviews = models.IntegerField(default=0)
    avg_overall = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    avg_helpfulness = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    avg_clarity = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    avg_expertise = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    avg_punctuality = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    avg_value = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    pct_5_star = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pct_would_rebook = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_review_summary"

    def __str__(self):
        return f"ReviewSummary — {self.provider} ({self.avg_overall}*)"
