"""CampusOS — Readiness views."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsFacultyOrAdvisor, IsPlacementOfficer, IsCampusAdmin
from apps.students.models import StudentProfile
from .models import (
    CompetencyScore,
    ImprovementPlan,
    ImprovementPlanTask,
    PlacementRiskFlag,
    ReadinessAssessment,
    ReadinessBenchmark,
    ReadinessCompetency,
    ReadinessGapAnalysis,
    WeeklyCareerAction,
)
from .serializers import (
    CompetencyScoreSerializer,
    ImprovementPlanSerializer,
    ImprovementPlanTaskSerializer,
    PlacementRiskFlagSerializer,
    ReadinessAssessmentSerializer,
    ReadinessBenchmarkSerializer,
    ReadinessCompetencySerializer,
    ReadinessGapAnalysisSerializer,
    WeeklyCareerActionSerializer,
)


class CompetencyListView(generics.ListAPIView):
    """List all active readiness competencies."""
    queryset = ReadinessCompetency.objects.filter(is_active=True)
    serializer_class = ReadinessCompetencySerializer
    permission_classes = [permissions.IsAuthenticated]


class MyReadinessAssessmentsView(generics.ListAPIView):
    """Student's own assessments."""
    serializer_class = ReadinessAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReadinessAssessment.objects.filter(
            student__user=self.request.user
        ).prefetch_related("competency_scores__competency")


class ReadinessAssessmentCreateView(generics.CreateAPIView):
    """Start a new readiness assessment."""
    serializer_class = ReadinessAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        student = get_object_or_404(StudentProfile, user=self.request.user)
        assessment = serializer.save(student=student)
        return assessment


class ReadinessAssessmentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ReadinessAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("faculty_advisor", "placement_officer", "campus_admin", "super_admin"):
            return ReadinessAssessment.objects.filter(student__campus=user.campus)
        return ReadinessAssessment.objects.filter(student__user=user)


class SubmitAssessmentView(APIView):
    """Submit assessment and compute overall score."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        assessment = get_object_or_404(ReadinessAssessment, id=pk, student__user=request.user)
        if assessment.status != "draft":
            return Response({"detail": "Already submitted."}, status=status.HTTP_400_BAD_REQUEST)
        score = assessment.compute_overall_score()
        label = self._get_label(score)
        assessment.overall_score = score
        assessment.score_label = label
        assessment.status = "submitted"
        assessment.save(update_fields=["overall_score", "score_label", "status"])
        return Response(ReadinessAssessmentSerializer(assessment).data)

    def _get_label(self, score):
        if score >= 80:
            return "Career-Ready"
        elif score >= 65:
            return "Placement-Ready"
        elif score >= 50:
            return "Developing"
        elif score >= 35:
            return "Emerging"
        return "Entry-Level"


class CompetencyScoreCreateView(generics.CreateAPIView):
    """Add a competency score to an assessment."""
    serializer_class = CompetencyScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        assessment_id = self.kwargs["assessment_id"]
        assessment = get_object_or_404(
            ReadinessAssessment, id=assessment_id, student__user=self.request.user
        )
        serializer.save(assessment=assessment)


class ImprovementPlanListCreateView(generics.ListCreateAPIView):
    serializer_class = ImprovementPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("faculty_advisor", "placement_officer", "campus_admin"):
            return ImprovementPlan.objects.filter(student__campus=user.campus)
        return ImprovementPlan.objects.filter(student__user=user)

    def perform_create(self, serializer):
        student = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=student, created_by=self.request.user)


class ImprovementPlanDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ImprovementPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("faculty_advisor", "placement_officer", "campus_admin"):
            return ImprovementPlan.objects.filter(student__campus=user.campus)
        return ImprovementPlan.objects.filter(student__user=user)


class ImprovementPlanTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = ImprovementPlanTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ImprovementPlanTask.objects.filter(plan_id=self.kwargs["plan_id"])

    def perform_create(self, serializer):
        plan = get_object_or_404(ImprovementPlan, id=self.kwargs["plan_id"])
        serializer.save(plan=plan)


class WeeklyCareerActionListCreateView(generics.ListCreateAPIView):
    serializer_class = WeeklyCareerActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WeeklyCareerAction.objects.filter(student__user=self.request.user)

    def perform_create(self, serializer):
        student = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=student)


class PlacementRiskFlagListView(generics.ListCreateAPIView):
    """Placement risk flags — staff view."""
    serializer_class = PlacementRiskFlagSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["risk_type", "severity", "status"]
    ordering_fields = ["severity", "created_at"]

    def get_queryset(self):
        return PlacementRiskFlag.objects.filter(
            student__campus=self.request.user.campus
        ).select_related("student__user")

    def perform_create(self, serializer):
        serializer.save(flagged_by=self.request.user)


class PlacementRiskFlagDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PlacementRiskFlagSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]

    def get_queryset(self):
        return PlacementRiskFlag.objects.filter(student__campus=self.request.user.campus)


class ReadinessBenchmarkView(generics.ListAPIView):
    """Campus-level readiness benchmarks."""
    serializer_class = ReadinessBenchmarkSerializer
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrAdvisor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["level", "program", "cohort_year"]

    def get_queryset(self):
        return ReadinessBenchmark.objects.filter(campus=self.request.user.campus)
