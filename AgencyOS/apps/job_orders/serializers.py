"""Job Orders serializers."""
from rest_framework import serializers
from .models import JobOrder, JobOrderNote, JobOrderStatusHistory


class JobOrderNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)

    class Meta:
        model = JobOrderNote
        fields = "__all__"
        read_only_fields = ["id", "author", "created_at"]


class JobOrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOrderStatusHistory
        fields = "__all__"
        read_only_fields = ["id", "changed_at"]


class JobOrderSerializer(serializers.ModelSerializer):
    notes_set = JobOrderNoteSerializer(many=True, read_only=True)
    status_history = JobOrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = JobOrder
        fields = "__all__"
        read_only_fields = ["id", "agency", "filled_count", "created_at", "updated_at"]


class JobOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    class Meta:
        model = JobOrder
        fields = [
            "id", "title", "staffing_type", "status", "priority", "positions_count",
            "filled_count", "target_fill_date", "assigned_recruiter", "created_at",
        ]
