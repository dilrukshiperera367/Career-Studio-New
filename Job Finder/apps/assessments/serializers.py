"""Assessments serializers."""
from rest_framework import serializers
from .models import Assessment, AssessmentQuestion, AssessmentAttempt


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    # Hide correct_answer for non-admins during attempt
    class Meta:
        model = AssessmentQuestion
        fields = [
            "id", "question_type", "question_text", "question_text_si", "question_text_ta",
            "options", "points", "sort_order",
        ]


class AssessmentQuestionWithAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = "__all__"


class AssessmentSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name_en", read_only=True, default="")
    category_name = serializers.CharField(source="category.name_en", read_only=True, default="")
    user_best_score = serializers.SerializerMethodField()
    user_passed = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            "id", "title", "title_si", "title_ta", "description",
            "skill_name", "category_name", "difficulty",
            "time_limit_minutes", "passing_score", "question_count",
            "is_active", "user_best_score", "user_passed",
        ]

    def get_user_best_score(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        attempt = obj.attempts.filter(user=request.user, completed_at__isnull=False).order_by("-score").first()
        return attempt.score if attempt else None

    def get_user_passed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.attempts.filter(user=request.user, passed=True).exists()


class AssessmentDetailSerializer(AssessmentSerializer):
    questions = AssessmentQuestionSerializer(many=True, read_only=True)

    class Meta(AssessmentSerializer.Meta):
        fields = AssessmentSerializer.Meta.fields + ["questions"]


class AssessmentAttemptSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(source="assessment.title", read_only=True)
    assessment_difficulty = serializers.CharField(source="assessment.difficulty", read_only=True)
    passing_score = serializers.IntegerField(source="assessment.passing_score", read_only=True)

    class Meta:
        model = AssessmentAttempt
        fields = [
            "id", "assessment", "assessment_title", "assessment_difficulty",
            "score", "total_points", "passed", "passing_score",
            "started_at", "completed_at", "time_spent_seconds",
        ]
        read_only_fields = ["score", "total_points", "passed", "completed_at"]


class AssessmentSubmitSerializer(serializers.Serializer):
    """Serializer for submitting answers to an assessment."""
    answers = serializers.DictField(
        child=serializers.JSONField(),
        help_text="Map of question_id → answer value",
    )
    time_spent_seconds = serializers.IntegerField(min_value=0, required=False, default=0)
