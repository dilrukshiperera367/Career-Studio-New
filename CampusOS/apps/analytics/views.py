"""CampusOS — Analytics app views (aggregation endpoints, no extra models needed)."""

from django.db.models import Count, Avg, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from apps.shared.permissions import IsPlacementOfficer
from apps.students.models import StudentProfile
from apps.readiness.models import ReadinessAssessment, PlacementRiskFlag
from apps.placements.models import PlacementDrive, DriveOffer, StudentDriveRegistration
from apps.internships.models import InternshipRecord
from apps.outcomes_analytics.models import CohortOutcome, PlacementOutcome


class StudentDashboardStatsView(APIView):
    """Aggregated stats for the current student's dashboard."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = StudentProfile.objects.filter(student=user).first()
        latest_assessment = ReadinessAssessment.objects.filter(student=user).order_by("-created_at").first()
        applications = StudentDriveRegistration.objects.filter(student=user)
        offers = DriveOffer.objects.filter(student=user)

        return Response({
            "profile_completion_pct": profile.profile_completion_pct if profile else 0,
            "readiness_score": latest_assessment.overall_score if latest_assessment else None,
            "total_applications": applications.count(),
            "pending_applications": applications.filter(status="registered").count(),
            "offers_received": offers.count(),
            "offers_accepted": offers.filter(status="accepted").count(),
        })


class PlacementOfficerDashboardView(APIView):
    """Placement officer — campus-wide overview."""
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get(self, request):
        campus = request.user.campus
        outcomes = PlacementOutcome.objects.filter(campus=campus)
        at_risk = PlacementRiskFlag.objects.filter(
            campus=campus, is_resolved=False
        ).values("severity").annotate(count=Count("id"))

        cohorts = CohortOutcome.objects.filter(campus=campus, is_published=True).order_by("-academic_year")

        return Response({
            "total_students_in_process": StudentProfile.objects.filter(
                student__campus=campus, placement_eligible=True
            ).count(),
            "total_placed": outcomes.filter(outcome_type="placed_campus_drive").count(),
            "total_offers": DriveOffer.objects.filter(drive__campus=campus).count(),
            "at_risk_by_severity": list(at_risk),
            "latest_cohort_placement_rate": cohorts.first().placement_rate_pct if cohorts.exists() else None,
            "active_drives": PlacementDrive.objects.filter(
                campus=campus, status__in=["announced", "registration_open", "ongoing"]
            ).count(),
        })


class ProgramPlacementStatsView(APIView):
    """Per-program placement breakdown for the current academic year."""
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get(self, request):
        campus = request.user.campus
        data = (
            PlacementOutcome.objects
            .filter(campus=campus)
            .values("program__name")
            .annotate(
                total=Count("id"),
                placed=Count("id", filter=Q(outcome_type="placed_campus_drive")),
                avg_ctc=Avg("ctc_annual_lkr"),
            )
        )
        return Response(list(data))
