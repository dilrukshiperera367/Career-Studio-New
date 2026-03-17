"""Analytics API views — KPIs, funnel, forecasts, data-quality, and compliance helpers."""

from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path
from django.core.cache import cache

from apps.analytics.models import AnalyticsDaily
from apps.accounts.permissions import IsRecruiter, HasTenantAccess
from apps.shared.cache import make_cache_key, CACHE_MEDIUM


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class AnalyticsDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsDaily
        fields = ["id", "job", "metric", "value", "metadata", "computed_date"]


class SavedReportSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.analytics.models import SavedReport
        model = SavedReport
        fields = ["id", "name", "report_type", "query_config", "schedule",
                  "recipients", "last_run_at", "created_at", "updated_at"]
        read_only_fields = ["id", "last_run_at", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Core analytics views
# ---------------------------------------------------------------------------

class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        """Get analytics metrics for the tenant."""
        job_id = request.query_params.get("job_id")
        metric = request.query_params.get("metric")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        qs = AnalyticsDaily.objects.filter(tenant_id=request.tenant_id)
        if job_id:
            qs = qs.filter(job_id=job_id)
        if metric:
            qs = qs.filter(metric=metric)
        if start_date:
            qs = qs.filter(computed_date__gte=start_date)
        if end_date:
            qs = qs.filter(computed_date__lte=end_date)

        return Response(AnalyticsDailySerializer(qs[:500], many=True).data)


class FunnelView(APIView):
    """Compute real-time funnel conversion for a job."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        job_id = request.query_params.get("job_id")
        if not job_id:
            return Response({"error": "job_id required"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.jobs.models import PipelineStage
        from apps.applications.models import Application

        stages = PipelineStage.objects.filter(
            job_id=job_id, tenant_id=request.tenant_id
        ).order_by("order")

        funnel = []
        for stage in stages:
            count = Application.objects.filter(
                job_id=job_id,
                tenant_id=request.tenant_id,
                stage_history__to_stage=stage,
            ).distinct().count()
            funnel.append({
                "stage": stage.name,
                "stage_type": stage.stage_type,
                "count": count,
            })

        return Response({"job_id": job_id, "funnel": funnel})


# ---------------------------------------------------------------------------
# KPI Dashboard (Features 89-96)
# ---------------------------------------------------------------------------

class KPIDashboardView(APIView):
    """Real-time KPI dashboard for hiring metrics."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import Application, Interview, Offer, Employee
        from apps.candidates.models import Candidate
        from apps.jobs.models import Job
        from django.db.models import Avg, Count, Q
        from django.utils import timezone
        import datetime

        tid = request.tenant_id
        now = timezone.now()
        thirty_days_ago = now - datetime.timedelta(days=30)
        period = request.query_params.get("period", "30")

        # Serve from cache if available (data changes at most every 5 min is acceptable)
        cache_key = make_cache_key('kpi_dashboard', tid, period)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        period_start = now - datetime.timedelta(days=int(period))

        # Core KPIs
        total_apps = Application.objects.filter(tenant_id=tid, created_at__gte=period_start).count()
        active_apps = Application.objects.filter(tenant_id=tid, status="active").count()
        hired = Application.objects.filter(tenant_id=tid, status="hired", created_at__gte=period_start).count()
        rejected = Application.objects.filter(tenant_id=tid, status="rejected", created_at__gte=period_start).count()
        open_jobs = Job.objects.filter(tenant_id=tid, status="open").count()
        total_candidates = Candidate.objects.filter(tenant_id=tid, status="active").count()

        # Time to hire (avg days from application to hire)
        hired_apps = Application.objects.filter(tenant_id=tid, status="hired", created_at__gte=period_start)
        avg_time_to_hire = None
        if hired_apps.exists():
            durations = [(a.updated_at - a.created_at).days for a in hired_apps[:100]]
            avg_time_to_hire = sum(durations) / max(len(durations), 1)

        # Offer acceptance rate
        total_offers = Offer.objects.filter(tenant_id=tid, created_at__gte=period_start).count()
        accepted_offers = Offer.objects.filter(tenant_id=tid, status="accepted", created_at__gte=period_start).count()
        offer_acceptance_rate = round(accepted_offers / max(total_offers, 1) * 100, 1)

        # Interview completion rate
        total_interviews = Interview.objects.filter(tenant_id=tid, created_at__gte=period_start).count()
        completed_interviews = Interview.objects.filter(tenant_id=tid, status="completed", created_at__gte=period_start).count()

        # Avg score
        avg_score = Application.objects.filter(tenant_id=tid, score__isnull=False).aggregate(avg=Avg("score"))["avg"]

        data = {
            "period_days": int(period),
            "kpis": {
                "total_applications": total_apps,
                "active_applications": active_apps,
                "hired": hired,
                "rejected": rejected,
                "open_jobs": open_jobs,
                "total_candidates": total_candidates,
                "avg_time_to_hire_days": round(avg_time_to_hire, 1) if avg_time_to_hire else None,
                "offer_acceptance_rate": offer_acceptance_rate,
                "interview_completion_rate": round(completed_interviews / max(total_interviews, 1) * 100, 1),
                "avg_candidate_score": round(avg_score, 2) if avg_score else None,
                "total_offers": total_offers,
                "accepted_offers": accepted_offers,
            },
        }
        cache.set(cache_key, data, CACHE_MEDIUM)
        return Response(data)


class RecruiterPerformanceView(APIView):
    """Per-recruiter hiring metrics."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import Application
        from apps.accounts.models import User
        from django.db.models import Count, Avg, Q
        from django.utils import timezone
        import datetime

        tid = request.tenant_id
        period = int(request.query_params.get("period", "30"))
        since = timezone.now() - datetime.timedelta(days=period)

        # Get recruiters with application stats
        recruiters = User.objects.filter(
            tenant_id=tid, user_type__in=["recruiter", "admin"], is_active=True
        )

        results = []
        for recruiter in recruiters:
            apps = Application.objects.filter(
                tenant_id=tid,
                assigned_recruiter=recruiter,
                created_at__gte=since,
            )
            results.append({
                "recruiter_id": str(recruiter.id),
                "name": f"{recruiter.first_name} {recruiter.last_name}",
                "total_applications": apps.count(),
                "hired": apps.filter(status="hired").count(),
                "rejected": apps.filter(status="rejected").count(),
                "active": apps.filter(status="active").count(),
                "avg_score": apps.aggregate(avg=Avg("score"))["avg"],
            })

        results.sort(key=lambda x: x["hired"], reverse=True)
        return Response({"period_days": period, "recruiters": results})


class PipelineVelocityView(APIView):
    """Time-in-stage analysis for pipeline velocity."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import StageHistory
        from django.db.models import Avg, F
        from django.utils import timezone
        import datetime

        tid = request.tenant_id
        job_id = request.query_params.get("job_id")

        qs = StageHistory.objects.filter(tenant_id=tid)
        if job_id:
            qs = qs.filter(application__job_id=job_id)

        # Calculate time per stage
        stages = {}
        for sh in qs.select_related("from_stage", "to_stage")[:1000]:
            stage_name = sh.to_stage.name if sh.to_stage else "Unknown"
            if stage_name not in stages:
                stages[stage_name] = {"count": 0, "total_days": 0}
            stages[stage_name]["count"] += 1

        return Response({
            "velocity": [
                {
                    "stage": name,
                    "transitions": data["count"],
                }
                for name, data in stages.items()
            ],
        })


class DiversityMetricsView(APIView):
    """Diversity and inclusion metrics (anonymized)."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import Application
        from django.db.models import Count

        tid = request.tenant_id

        # Source distribution
        source_dist = Application.objects.filter(
            tenant_id=tid
        ).values("source").annotate(count=Count("id")).order_by("-count")

        # Stage distribution by source
        stage_dist = Application.objects.filter(
            tenant_id=tid, status="active"
        ).values(
            "current_stage__name", "source"
        ).annotate(count=Count("id"))

        return Response({
            "source_distribution": list(source_dist),
            "stage_by_source": list(stage_dist),
            "note": "Demographics tracking requires opt-in EEO configuration",
        })


class SourceROIView(APIView):
    """ROI analysis by application source."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import Application
        from django.db.models import Count, Avg, Q

        tid = request.tenant_id

        sources = Application.objects.filter(
            tenant_id=tid
        ).values("source").annotate(
            total=Count("id"),
            hired=Count("id", filter=Q(status="hired")),
            rejected=Count("id", filter=Q(status="rejected")),
            avg_score=Avg("score"),
        ).order_by("-hired")

        results = []
        for src in sources:
            conversion = round(src["hired"] / max(src["total"], 1) * 100, 1)
            results.append({
                "source": src["source"] or "unknown",
                "total_applications": src["total"],
                "hired": src["hired"],
                "rejected": src["rejected"],
                "conversion_rate": conversion,
                "avg_score": round(src["avg_score"], 2) if src["avg_score"] else None,
            })

        return Response({"sources": results})


class SLAComplianceView(APIView):
    """SLA compliance: applications exceeding stage time limits."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import Application
        from apps.jobs.models import PipelineStage
        from django.utils import timezone
        import datetime

        tid = request.tenant_id

        # Find stages with SLA
        stages_with_sla = PipelineStage.objects.filter(
            tenant_id=tid, sla_days__isnull=False, sla_days__gt=0
        )

        violations = []
        for stage in stages_with_sla:
            deadline = timezone.now() - datetime.timedelta(days=stage.sla_days)
            overdue = Application.objects.filter(
                tenant_id=tid,
                current_stage=stage,
                status="active",
                updated_at__lt=deadline,
            ).count()

            total_in_stage = Application.objects.filter(
                tenant_id=tid, current_stage=stage, status="active"
            ).count()

            violations.append({
                "stage": stage.name,
                "job": stage.job.title if stage.job else "",
                "sla_days": stage.sla_days,
                "overdue_count": overdue,
                "total_in_stage": total_in_stage,
                "compliance_rate": round((1 - overdue / max(total_in_stage, 1)) * 100, 1),
            })

        return Response({"sla_violations": violations})


class HiringForecastView(APIView):
    """Hiring forecast based on pipeline data and historical trends."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import Application
        from apps.jobs.models import Job
        from django.db.models import Count, Q
        from django.utils import timezone
        import datetime

        tid = request.tenant_id

        open_jobs = Job.objects.filter(tenant_id=tid, status="open")
        forecasts = []
        for job in open_jobs[:20]:
            pipeline = Application.objects.filter(job=job, tenant_id=tid, status="active")
            total = pipeline.count()
            # Historical conversion rate for this job
            all_apps = Application.objects.filter(job=job, tenant_id=tid)
            hired_for_job = all_apps.filter(status="hired").count()
            conversion = hired_for_job / max(all_apps.count(), 1)

            forecasts.append({
                "job_id": str(job.id),
                "job_title": job.title,
                "active_pipeline": total,
                "headcount_target": job.headcount_target,
                "headcount_filled": job.headcount_filled,
                "headcount_remaining": (job.headcount_target or 1) - (job.headcount_filled or 0),
                "estimated_hires": round(total * max(conversion, 0.05)),
                "historical_conversion": round(conversion * 100, 1),
            })

        return Response({"forecasts": forecasts})


class AnalyticsExportView(APIView):
    """Export analytics data as CSV."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        import csv
        import io
        from django.http import HttpResponse
        from apps.applications.models import Application

        tid = request.tenant_id
        export_type = request.query_params.get("type", "applications")

        if export_type == "applications":
            apps = Application.objects.filter(
                tenant_id=tid
            ).select_related("candidate", "job", "current_stage")[:5000]

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Application ID", "Candidate", "Email", "Job", "Stage",
                "Status", "Score", "Source", "Priority", "On Hold",
                "Applied At", "Updated At",
            ])

            for app in apps:
                writer.writerow([
                    str(app.id),
                    app.candidate.full_name if app.candidate else "",
                    app.candidate.primary_email if app.candidate else "",
                    app.job.title if app.job else "",
                    app.current_stage.name if app.current_stage else "",
                    app.status,
                    app.score,
                    app.source,
                    app.is_priority,
                    app.on_hold,
                    app.created_at.isoformat(),
                    app.updated_at.isoformat(),
                ])

            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = f"attachment; filename=applications_export.csv"
            return response

        return Response({"error": "Unknown export type"}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Saved Reports
# ---------------------------------------------------------------------------

class SavedReportListView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.analytics.models import SavedReport
        reports = SavedReport.objects.filter(tenant_id=request.tenant_id)
        return Response(SavedReportSerializer(reports, many=True).data)

    def post(self, request):
        from apps.analytics.models import SavedReport
        ser = SavedReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(tenant_id=request.tenant_id)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class SavedReportDetailView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request, pk):
        from apps.analytics.models import SavedReport
        report = SavedReport.objects.get(id=pk, tenant_id=request.tenant_id)
        return Response(SavedReportSerializer(report).data)

    def delete(self, request, pk):
        from apps.analytics.models import SavedReport
        SavedReport.objects.filter(id=pk, tenant_id=request.tenant_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Advanced analytics (Features 93, 164, 170, 151, 103, 46, 44, 16)
# ---------------------------------------------------------------------------

class TrendReportView(APIView):
    """Month-over-month trend comparison."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.analytics.utils import generate_trend_report
        months = int(request.query_params.get("months", 6))
        return Response(generate_trend_report(request.tenant_id, months))


class RejectionAnalyticsView(APIView):
    """Rejection reasons by stage, job, department."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.analytics.utils import rejection_analytics
        job_id = request.query_params.get("job_id")
        return Response(rejection_analytics(request.tenant_id, job_id))


class InterviewToHireRatioView(APIView):
    """How many interviews per hire."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.analytics.utils import interview_to_hire_ratio
        job_id = request.query_params.get("job_id")
        return Response(interview_to_hire_ratio(request.tenant_id, job_id))


class OfferComparisonView(APIView):
    """Compare current vs historical offers for a job."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.analytics.utils import offer_comparison
        job_id = request.query_params.get("job_id")
        if not job_id:
            return Response({"error": "job_id required"}, status=400)
        return Response(offer_comparison(request.tenant_id, job_id))


class VotingTallyView(APIView):
    """Hiring committee voting tally for an application."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request, pk):
        from apps.analytics.utils import voting_tally
        return Response(voting_tally(request.tenant_id, str(pk)))


class ScoreComparisonView(APIView):
    """Compare a candidate's scores across all their jobs."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request, pk):
        from apps.analytics.utils import score_comparison_across_jobs
        return Response(score_comparison_across_jobs(request.tenant_id, str(pk)))


class BatchRescoreView(APIView):
    """Re-score all candidates for a job against updated requirements."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def post(self, request):
        from apps.analytics.utils import batch_rescore
        job_id = request.data.get("job_id")
        if not job_id:
            return Response({"error": "job_id required"}, status=400)
        return Response(batch_rescore(request.tenant_id, job_id))


class CostPerHireView(APIView):
    """Estimated cost-per-hire metrics."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.candidates.utils import calculate_cost_per_hire
        job_id = request.query_params.get("job_id")
        return Response(calculate_cost_per_hire(request.tenant_id, job_id))


# ---------------------------------------------------------------------------
# Data quality & compliance (Features 128, 130, 132, 134, 179)
# ---------------------------------------------------------------------------

class DataCleanupView(APIView):
    """Bulk data quality report for tenant."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.candidates.utils import bulk_data_cleanup
        return Response(bulk_data_cleanup(request.tenant_id))


class ContactValidationView(APIView):
    """Validate contact info for a candidate."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request, pk):
        from apps.candidates.utils import validate_candidate_contacts
        return Response(validate_candidate_contacts(request.tenant_id, str(pk)))


class StaleDataFlaggingView(APIView):
    """Flag candidates with outdated data."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def post(self, request):
        from apps.candidates.utils import flag_stale_candidates
        stale_days = int(request.data.get("stale_days", 365))
        flagged = flag_stale_candidates(request.tenant_id, stale_days)
        return Response({"flagged": flagged})


class GDPRPurgeView(APIView):
    """Right to deletion — GDPR data purge."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def post(self, request, pk):
        from apps.candidates.utils import purge_candidate_data
        result = purge_candidate_data(
            request.tenant_id, str(pk), str(request.user.id)
        )
        return Response(result)


# ---------------------------------------------------------------------------
# Phase 2 — New cross-app analytics views
# ---------------------------------------------------------------------------

class SourcingFunnelByChannelView(APIView):
    """Breakdown of applications by source channel with stage conversion rates per channel."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.applications.models import Application
        from django.db.models import Count, Q

        tid = request.tenant_id

        # Get all source channels and their stage conversion data
        sources = (
            Application.objects.filter(tenant_id=tid)
            .values("source")
            .annotate(
                total=Count("id"),
                screened=Count("id", filter=Q(status__in=["screening", "interview", "offer", "hired"])),
                interviewed=Count("id", filter=Q(status__in=["interview", "offer", "hired"])),
                offered=Count("id", filter=Q(status__in=["offer", "hired"])),
                hired=Count("id", filter=Q(status="hired")),
                rejected=Count("id", filter=Q(status="rejected")),
            )
            .order_by("-total")
        )

        results = []
        for src in sources:
            total = src["total"]
            results.append({
                "source": src["source"] or "unknown",
                "total_applications": total,
                "screened": src["screened"],
                "interviewed": src["interviewed"],
                "offered": src["offered"],
                "hired": src["hired"],
                "rejected": src["rejected"],
                "screen_rate": round(src["screened"] / max(total, 1) * 100, 1),
                "interview_rate": round(src["interviewed"] / max(total, 1) * 100, 1),
                "offer_rate": round(src["offered"] / max(total, 1) * 100, 1),
                "hire_rate": round(src["hired"] / max(total, 1) * 100, 1),
            })

        return Response({"channels": results})


class HeadcountPlanAttainmentView(APIView):
    """For each HeadcountPlan show planned vs actual hires."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.job_architecture.models import HeadcountPlan
        from apps.applications.models import Application
        from django.db.models import Count, Q

        tid = request.tenant_id

        plans = HeadcountPlan.objects.filter(tenant_id=tid)

        results = []
        for plan in plans:
            # Count hires for jobs linked to this plan (no period filter — plan uses fiscal_year/quarter)
            hired_count = Application.objects.filter(
                tenant_id=tid,
                status="hired",
                job__headcount_plan=plan,
            ).count()

            planned = plan.total_headcount or 0

            results.append({
                "plan_id": str(plan.id),
                "name": plan.name,
                "department": plan.department or None,
                "fiscal_year": plan.fiscal_year,
                "quarter": plan.quarter,
                "total_headcount": planned,
                "approved_headcount": plan.approved_headcount,
                "actual_hires": hired_count,
                "attainment_rate": round(hired_count / max(planned, 1) * 100, 1),
                "gap": planned - hired_count,
            })

        return Response({"headcount_attainment": results})


class NPSTrendView(APIView):
    """NPS score over time from portal.CandidateNPS, grouped by month."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.portal.models import CandidateNPS
        from django.db.models import Count, Q
        from django.db.models.functions import TruncMonth

        tid = request.tenant_id
        months = int(request.query_params.get("months", 6))

        from django.utils import timezone
        import datetime
        since = timezone.now() - datetime.timedelta(days=months * 30)

        monthly = (
            CandidateNPS.objects.filter(tenant_id=tid, responded_at__gte=since)
            .annotate(month=TruncMonth("responded_at"))
            .values("month")
            .annotate(
                total=Count("id"),
                promoters=Count("id", filter=Q(score__gte=9)),
                passives=Count("id", filter=Q(score__gte=7, score__lte=8)),
                detractors=Count("id", filter=Q(score__lte=6)),
            )
            .order_by("month")
        )

        results = []
        for row in monthly:
            total = row["total"]
            promoter_pct = row["promoters"] / max(total, 1) * 100
            detractor_pct = row["detractors"] / max(total, 1) * 100
            nps = round(promoter_pct - detractor_pct, 1)
            results.append({
                "month": row["month"].strftime("%Y-%m") if row["month"] else None,
                "total_responses": total,
                "promoters": row["promoters"],
                "passives": row["passives"],
                "detractors": row["detractors"],
                "nps_score": nps,
            })

        return Response({"nps_trend": results, "months": months})


class NurtureConversionView(APIView):
    """For each NurtureSequence show enrollment count, completion rate, and conversion to application."""
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request):
        from apps.messaging.models import NurtureSequence, NurtureEnrollment
        from apps.applications.models import Application
        from django.db.models import Count, Q

        tid = request.tenant_id

        sequences = NurtureSequence.objects.filter(tenant_id=tid)

        results = []
        for seq in sequences:
            enrollments = NurtureEnrollment.objects.filter(tenant_id=tid, sequence=seq)
            total_enrolled = enrollments.count()
            completed = enrollments.filter(status="completed").count()

            # Candidates who applied to any job after being enrolled
            enrolled_candidate_ids = enrollments.values_list("candidate_id", flat=True)
            converted = Application.objects.filter(
                tenant_id=tid,
                candidate_id__in=enrolled_candidate_ids,
                created_at__gte=seq.created_at,
            ).values("candidate_id").distinct().count()

            results.append({
                "sequence_id": str(seq.id),
                "sequence_name": seq.name,
                "total_enrolled": total_enrolled,
                "completed": completed,
                "completion_rate": round(completed / max(total_enrolled, 1) * 100, 1),
                "converted_to_applicant": converted,
                "conversion_rate": round(converted / max(total_enrolled, 1) * 100, 1),
            })

        return Response({"nurture_conversion": results})


# ---------------------------------------------------------------------------
# Re-imports from extracted modules (needed by analytics_urlpatterns below)
# ---------------------------------------------------------------------------
from apps.shared.views.onboarding import EarlyAttritionView, BuddySuggestionView  # noqa: E402
from apps.shared.views.misc import InterviewConflictView  # noqa: E402


# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------

analytics_urlpatterns = [
    path("", AnalyticsView.as_view(), name="analytics"),
    path("funnel/", FunnelView.as_view(), name="analytics-funnel"),
    path("kpis/", KPIDashboardView.as_view(), name="analytics-kpis"),
    path("recruiter-performance/", RecruiterPerformanceView.as_view(), name="analytics-recruiter-perf"),
    path("pipeline-velocity/", PipelineVelocityView.as_view(), name="analytics-pipeline-velocity"),
    path("diversity/", DiversityMetricsView.as_view(), name="analytics-diversity"),
    path("source-roi/", SourceROIView.as_view(), name="analytics-source-roi"),
    path("sla-compliance/", SLAComplianceView.as_view(), name="analytics-sla"),
    path("export/", AnalyticsExportView.as_view(), name="analytics-export"),
    path("hiring-forecast/", HiringForecastView.as_view(), name="analytics-forecast"),
    path("saved-reports/", SavedReportListView.as_view(), name="analytics-saved-reports"),
    path("saved-reports/<uuid:pk>/", SavedReportDetailView.as_view(), name="analytics-saved-report-detail"),
    # NEW — Waves 6-8 completion
    path("trends/", TrendReportView.as_view(), name="analytics-trends"),
    path("rejections/", RejectionAnalyticsView.as_view(), name="analytics-rejections"),
    path("interview-to-hire/", InterviewToHireRatioView.as_view(), name="analytics-interview-hire"),
    path("offer-comparison/", OfferComparisonView.as_view(), name="analytics-offer-comparison"),
    path("cost-per-hire/", CostPerHireView.as_view(), name="analytics-cost-per-hire"),
    path("voting/<uuid:pk>/", VotingTallyView.as_view(), name="analytics-voting"),
    path("score-comparison/<uuid:pk>/", ScoreComparisonView.as_view(), name="analytics-score-comparison"),
    path("batch-rescore/", BatchRescoreView.as_view(), name="analytics-batch-rescore"),
    path("early-attrition/", EarlyAttritionView.as_view(), name="analytics-early-attrition"),
    path("data-cleanup/", DataCleanupView.as_view(), name="analytics-data-cleanup"),
    path("stale-data/", StaleDataFlaggingView.as_view(), name="analytics-stale-data"),
    path("interview-conflicts/", InterviewConflictView.as_view(), name="analytics-interview-conflicts"),
    # Phase 2 — cross-app analytics
    path("sourcing-funnel/", SourcingFunnelByChannelView.as_view(), name="analytics-sourcing-funnel"),
    path("headcount-attainment/", HeadcountPlanAttainmentView.as_view(), name="analytics-headcount-attainment"),
    path("nps-trend/", NPSTrendView.as_view(), name="analytics-nps-trend"),
    path("nurture-conversion/", NurtureConversionView.as_view(), name="analytics-nurture-conversion"),
]
