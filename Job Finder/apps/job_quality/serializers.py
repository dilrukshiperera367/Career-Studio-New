"""Job Quality — serializers."""
from rest_framework import serializers
from .models import JobQualityScore, DuplicateJobGroup, ScamPattern, FreshnessSignal


class JobQualityScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobQualityScore
        fields = [
            "job_id", "overall_score", "freshness_score", "completeness_score", "trust_score",
            "scam_risk", "scam_signals", "has_salary", "has_requirements", "has_benefits",
            "is_duplicate", "last_scored_at", "score_version",
        ]


class ScamPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScamPattern
        fields = "__all__"


class FreshnessSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreshnessSignal
        fields = ["id", "job_id", "signal_type", "freshness_delta", "created_at"]
