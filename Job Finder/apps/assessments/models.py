"""Assessments app — Skill assessments and tests."""
import uuid
from django.db import models
from django.conf import settings


class Assessment(models.Model):
    """A skill assessment / quiz that can be linked to jobs or taken by seekers."""

    class DifficultyLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    title_si = models.CharField(max_length=200, blank=True, default="")
    title_ta = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    skill = models.ForeignKey("taxonomy.Skill", on_delete=models.SET_NULL, null=True, blank=True, related_name="assessments")
    category = models.ForeignKey("taxonomy.JobCategory", on_delete=models.SET_NULL, null=True, blank=True)
    difficulty = models.CharField(max_length=15, choices=DifficultyLevel.choices, default=DifficultyLevel.INTERMEDIATE)
    time_limit_minutes = models.IntegerField(default=30)
    passing_score = models.IntegerField(default=70)
    question_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_assessments"


class AssessmentQuestion(models.Model):
    """Individual question within an assessment."""

    class QuestionType(models.TextChoices):
        MCQ = "mcq", "Multiple Choice"
        TRUE_FALSE = "true_false", "True/False"
        SHORT_ANSWER = "short_answer", "Short Answer"
        CODE = "code", "Code"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=15, choices=QuestionType.choices, default=QuestionType.MCQ)
    question_text = models.TextField()
    question_text_si = models.TextField(blank=True, default="")
    question_text_ta = models.TextField(blank=True, default="")
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.JSONField(default=dict)
    explanation = models.TextField(blank=True, default="")
    points = models.IntegerField(default=1)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_assessment_questions"
        ordering = ["sort_order"]


class AssessmentAttempt(models.Model):
    """A user's attempt at an assessment."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_attempts")
    score = models.IntegerField(null=True, blank=True)
    total_points = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    answers = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "jf_assessment_attempts"
        ordering = ["-started_at"]
