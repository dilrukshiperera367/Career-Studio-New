"""Job Quality — views."""
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobListing
from .models import JobQualityScore, ScamPattern, FreshnessSignal, DuplicateJobGroup
from .serializers import JobQualityScoreSerializer, ScamPatternSerializer, FreshnessSignalSerializer


class JobQualityScoreView(APIView):
    """Get quality score details for a job listing."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        try:
            score = JobQualityScore.objects.get(job_id=job_id)
        except JobQualityScore.DoesNotExist:
            # Create a basic score if not yet scored
            try:
                job = JobListing.objects.get(pk=job_id)
                score = _compute_quality_score(job)
            except JobListing.DoesNotExist:
                return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(JobQualityScoreSerializer(score).data)


class DuplicateCheckView(APIView):
    """Check if a job is a detected duplicate."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            score = JobQualityScore.objects.get(job_id=job_id)
        except JobQualityScore.DoesNotExist:
            return Response({"is_duplicate": False, "group_id": None})
        return Response({
            "is_duplicate": score.is_duplicate,
            "group_id": str(score.duplicate_group_id) if score.duplicate_group_id else None,
        })


class ScamRiskView(APIView):
    """Get scam risk assessment for a job."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        try:
            score = JobQualityScore.objects.get(job_id=job_id)
        except JobQualityScore.DoesNotExist:
            return Response({"scam_risk": "none", "scam_signals": []})
        return Response({"scam_risk": score.scam_risk, "scam_signals": score.scam_signals})


class ScamPatternViewSet(viewsets.ModelViewSet):
    """Admin-managed scam pattern library."""
    queryset = ScamPattern.objects.filter(is_active=True)
    serializer_class = ScamPatternSerializer
    permission_classes = [permissions.IsAdminUser]


def _compute_quality_score(job):
    """Compute and save a JobQualityScore for a job listing."""
    completeness = 0
    if job.description:
        completeness += 20
    if job.requirements:
        completeness += 15
    if job.benefits:
        completeness += 10
    if job.salary_min:
        completeness += 15
    if job.required_skills.exists():
        completeness += 10
    if job.expires_at:
        completeness += 5
    if job.screening_questions:
        completeness += 5
    completeness = min(completeness, 80)

    # Freshness based on published_at age
    from datetime import timedelta
    from django.utils import timezone
    age_days = (timezone.now() - job.published_at).days if job.published_at else 365
    freshness = max(0, 100 - (age_days * 2))

    score, _ = JobQualityScore.objects.update_or_create(
        job=job,
        defaults={
            "overall_score": (freshness * 0.4 + completeness * 0.6),
            "freshness_score": freshness,
            "completeness_score": float(completeness),
            "has_salary": bool(job.salary_min),
            "has_requirements": bool(job.requirements),
            "has_benefits": bool(job.benefits),
        }
    )
    return score
