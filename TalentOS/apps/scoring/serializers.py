"""Serializers for the scoring app."""

from rest_framework import serializers
from apps.scoring.models import (
    JobScoreBatch, BatchItem, BatchItemScore,
    CandidateProfile, CandidateResumeVersion, CandidateScoreRun,
)


# ===========================================================================
# Company — Batch scoring
# ===========================================================================

class BatchItemScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchItemScore
        fields = [
            "id", "score_total",
            "content_score", "title_score", "experience_score",
            "recency_score", "format_score", "breakdown_json",
        ]


class BatchItemSerializer(serializers.ModelSerializer):
    score = BatchItemScoreSerializer(read_only=True)

    class Meta:
        model = BatchItem
        fields = [
            "id", "file_name", "file_type", "status",
            "candidate_name", "candidate_email",
            "error_message", "created_at", "score",
        ]


class JobScoreBatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view."""
    class Meta:
        model = JobScoreBatch
        fields = [
            "id", "job_title", "status",
            "total_items", "parsed_items", "scored_items",
            "created_at",
        ]


class JobScoreBatchDetailSerializer(serializers.ModelSerializer):
    items = BatchItemSerializer(many=True, read_only=True)

    class Meta:
        model = JobScoreBatch
        fields = [
            "id", "job_title", "jd_text", "jd_requirements_json",
            "scoring_weights", "status",
            "total_items", "parsed_items", "scored_items",
            "created_at", "updated_at", "items",
        ]


class CreateBatchSerializer(serializers.Serializer):
    """Input for creating a scoring batch."""
    job_title = serializers.CharField(max_length=300, required=False, default="")
    jd_text = serializers.CharField()
    scoring_weights = serializers.JSONField(required=False, default=dict)


# ===========================================================================
# Candidate — Personal scoring
# ===========================================================================

class CandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = ["id", "headline", "phone", "location", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CandidateResumeVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateResumeVersion
        fields = [
            "id", "file_name", "file_type", "version_label",
            "is_primary", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CandidateScoreRunListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateScoreRun
        fields = [
            "id", "jd_title", "score_total",
            "content_score", "title_score", "experience_score",
            "recency_score", "format_score", "created_at",
        ]


class CandidateScoreRunDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateScoreRun
        fields = [
            "id", "jd_title", "jd_text", "jd_requirements_json",
            "score_total", "content_score", "title_score",
            "experience_score", "recency_score", "format_score",
            "breakdown_json", "created_at",
        ]
