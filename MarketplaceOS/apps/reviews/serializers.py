from rest_framework import serializers
from .models import Review, ProviderResponse, ReviewFlag, OutcomeTag, ReviewSummary


class OutcomeTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutcomeTag
        fields = ["slug", "label", "category"]


class ProviderResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderResponse
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ReviewSerializer(serializers.ModelSerializer):
    outcome_tag_slugs = serializers.SlugRelatedField(
        many=True, queryset=OutcomeTag.objects.filter(is_active=True),
        slug_field="slug", source="outcome_tags", required=False,
    )
    provider_response = ProviderResponseSerializer(read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_moderation_status_display", read_only=True)

    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = [
            "id", "provider", "reviewer", "moderation_status", "moderation_notes",
            "moderated_by", "moderated_at", "authenticity_score", "is_suspicious",
            "authenticity_flags", "helpful_votes", "unhelpful_votes",
            "created_at", "updated_at",
        ]

    def get_reviewer_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.reviewer.get_full_name() or obj.reviewer.email


class ReviewListSerializer(serializers.ModelSerializer):
    """Lightweight read serializer for provider profile review cards."""
    reviewer_name = serializers.SerializerMethodField()
    outcome_tags = OutcomeTagSerializer(many=True, read_only=True)
    provider_response = ProviderResponseSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "rating_overall", "rating_helpfulness", "rating_clarity",
            "rating_expertise", "rating_punctuality", "rating_value",
            "headline", "body", "outcome_tags", "would_recommend", "would_rebook",
            "is_featured", "reviewer_name", "provider_response",
            "helpful_votes", "created_at",
        ]

    def get_reviewer_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.reviewer.get_full_name() or obj.reviewer.email


class ReviewFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewFlag
        fields = "__all__"
        read_only_fields = ["id", "status", "resolved_by", "resolved_at", "created_at"]


class ReviewSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewSummary
        fields = "__all__"
        read_only_fields = ["provider", "updated_at"]
