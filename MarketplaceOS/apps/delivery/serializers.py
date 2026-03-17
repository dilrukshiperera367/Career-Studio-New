from rest_framework import serializers
from .models import (
    Session, SessionNote, SessionDeliverable, SessionFeedbackForm,
    SessionActionPlan, SessionMilestone, SessionAssignment,
    MockInterviewRubric, AsyncReviewDelivery,
)


class SessionNoteSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = SessionNote
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SessionDeliverableSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionDeliverable
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class SessionFeedbackFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionFeedbackForm
        fields = "__all__"
        read_only_fields = ["id", "created_at", "submitted_by"]


class SessionMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionMilestone
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class SessionActionPlanSerializer(serializers.ModelSerializer):
    milestones = SessionMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = SessionActionPlan
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SessionAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionAssignment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "submitted_at", "reviewed_at"]


class MockInterviewRubricSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockInterviewRubric
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AsyncReviewDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = AsyncReviewDelivery
        fields = "__all__"
        read_only_fields = ["id"]


class SessionSerializer(serializers.ModelSerializer):
    notes = SessionNoteSerializer(many=True, read_only=True)
    deliverables = SessionDeliverableSerializer(many=True, read_only=True)
    assignments = SessionAssignmentSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Session
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "started_at", "ended_at"]
