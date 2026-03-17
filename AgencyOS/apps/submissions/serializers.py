"""Submissions serializers."""
from rest_framework import serializers
from .models import CandidateProfile, Submission, SubmissionStatusHistory, Shortlist, SendToClientLog


class CandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class CandidateProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = [
            "id", "first_name", "last_name", "email", "city", "country",
            "ownership_status", "available_from", "contract_preference",
            "quality_score", "do_not_submit", "created_at",
        ]


class SubmissionStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionStatusHistory
        fields = "__all__"
        read_only_fields = ["id", "changed_at"]


class SubmissionSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    status_history = SubmissionStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]

    def get_candidate_name(self, obj):
        return f"{obj.candidate.first_name} {obj.candidate.last_name}"


class SubmissionListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id", "candidate", "candidate_name", "job_order", "status",
            "match_score", "rank_in_shortlist", "sent_to_client_at", "created_at",
        ]

    def get_candidate_name(self, obj):
        return f"{obj.candidate.first_name} {obj.candidate.last_name}"


class ShortlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shortlist
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class SendToClientLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SendToClientLog
        fields = "__all__"
        read_only_fields = ["id", "sent_at"]
