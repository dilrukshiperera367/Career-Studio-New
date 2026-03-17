"""Moderation serializers."""
from rest_framework import serializers
from .models import Report, ModerationAction


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["content_type", "content_id", "reason", "description", "evidence"]


class ReportSerializer(serializers.ModelSerializer):
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True, default="")

    class Meta:
        model = Report
        fields = [
            "id", "reporter", "reporter_email", "content_type", "content_id",
            "reason", "description", "evidence", "status",
            "reviewed_by", "resolution_notes", "resolved_at", "created_at",
        ]
        read_only_fields = fields


class ReportResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("resolved", "Resolved"), ("dismissed", "Dismissed")])
    resolution_notes = serializers.CharField(required=False, default="")
    action = serializers.ChoiceField(
        required=False, default="",
        choices=[("", "None"), ("warn", "Warn"), ("remove", "Remove"), ("suspend", "Suspend"), ("ban", "Ban")],
    )


class ModerationActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModerationAction
        fields = ["id", "moderator", "report", "action", "target_type", "target_id", "notes", "created_at"]
        read_only_fields = fields
