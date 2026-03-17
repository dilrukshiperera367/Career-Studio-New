"""Assessments views — Browse, take, and review skill assessments."""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assessment, AssessmentQuestion, AssessmentAttempt
from .serializers import (
    AssessmentSerializer, AssessmentDetailSerializer,
    AssessmentAttemptSerializer, AssessmentSubmitSerializer,
)


class AssessmentListView(generics.ListAPIView):
    """Browse available assessments, optionally filtered by skill/difficulty."""
    serializer_class = AssessmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Assessment.objects.filter(is_active=True)
        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        skill = self.request.query_params.get("skill")
        if skill:
            qs = qs.filter(skill_id=skill)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)
        return qs.order_by("difficulty", "title")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class AssessmentDetailView(generics.RetrieveAPIView):
    """Retrieve a single assessment with its questions (answers hidden)."""
    serializer_class = AssessmentDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Assessment.objects.filter(is_active=True)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class StartAssessmentView(APIView):
    """Start a new attempt — creates the AssessmentAttempt record."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            assessment = Assessment.objects.get(pk=pk, is_active=True)
        except Assessment.DoesNotExist:
            return Response({"detail": "Assessment not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if there's an in-progress attempt
        in_progress = AssessmentAttempt.objects.filter(
            assessment=assessment, user=request.user, completed_at__isnull=True,
        ).first()
        if in_progress:
            return Response(
                AssessmentAttemptSerializer(in_progress).data,
                status=status.HTTP_200_OK,
            )

        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            user=request.user,
        )
        return Response(AssessmentAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)


class SubmitAssessmentView(APIView):
    """Submit answers and calculate score."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(
                pk=attempt_id, user=request.user, completed_at__isnull=True,
            )
        except AssessmentAttempt.DoesNotExist:
            return Response({"detail": "Attempt not found or already completed."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssessmentSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_answers = serializer.validated_data["answers"]
        time_spent = serializer.validated_data.get("time_spent_seconds", 0)

        # Grade answers
        questions = attempt.assessment.questions.all()
        total_points = sum(q.points for q in questions)
        earned_points = 0

        for question in questions:
            q_id = str(question.id)
            user_ans = user_answers.get(q_id)
            correct = question.correct_answer

            if question.question_type == "mcq":
                if user_ans == correct.get("answer"):
                    earned_points += question.points
            elif question.question_type == "true_false":
                if str(user_ans).lower() == str(correct.get("answer", "")).lower():
                    earned_points += question.points
            elif question.question_type == "short_answer":
                expected = correct.get("answer", "").strip().lower()
                if user_ans and user_ans.strip().lower() == expected:
                    earned_points += question.points

        score = int((earned_points / total_points * 100)) if total_points > 0 else 0
        passed = score >= attempt.assessment.passing_score

        attempt.answers = user_answers
        attempt.score = score
        attempt.total_points = total_points
        attempt.passed = passed
        attempt.completed_at = timezone.now()
        attempt.time_spent_seconds = time_spent
        attempt.save()

        return Response({
            "attempt_id": str(attempt.id),
            "score": score,
            "total_points": total_points,
            "earned_points": earned_points,
            "passed": passed,
            "passing_score": attempt.assessment.passing_score,
            "time_spent_seconds": time_spent,
        })


class MyAssessmentAttemptsView(generics.ListAPIView):
    """List current user's assessment attempts (history)."""
    serializer_class = AssessmentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AssessmentAttempt.objects.filter(
            user=self.request.user, completed_at__isnull=False,
        ).select_related("assessment").order_by("-completed_at")


class AssessmentResultView(generics.RetrieveAPIView):
    """Get result of a specific attempt with question-by-question breakdown."""
    serializer_class = AssessmentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AssessmentAttempt.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        attempt = self.get_object()
        data = AssessmentAttemptSerializer(attempt).data

        # Build per-question breakdown
        questions = attempt.assessment.questions.all()
        breakdown = []
        for q in questions:
            q_id = str(q.id)
            user_ans = attempt.answers.get(q_id)
            correct_ans = q.correct_answer.get("answer")
            is_correct = False
            if q.question_type in ("mcq", "true_false"):
                is_correct = str(user_ans).lower() == str(correct_ans).lower() if user_ans is not None else False
            elif q.question_type == "short_answer":
                is_correct = (user_ans or "").strip().lower() == (correct_ans or "").strip().lower()

            breakdown.append({
                "question_id": q_id,
                "question_text": q.question_text,
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": q.explanation,
                "points": q.points,
            })

        data["breakdown"] = breakdown
        return Response(data)
