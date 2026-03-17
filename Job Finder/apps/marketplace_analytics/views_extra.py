"""
Feature 16 — Marketplace Analytics & Growth Intelligence
Feature 17 — Employer Analytics & ROI

Views for marketplace_analytics app:
- Supply/demand dashboards
- Conversion funnel by page type
- Search-to-apply conversion
- Alert open/click/apply metrics
- Company-page engagement
- Fraud/abuse dashboards
- Duplicate-job rates
- SEO landing-page performance
- City/category liquidity dashboards
- Cohort retention
- LTV by employer type
- CAC by acquisition channel
- Candidate engagement scoring
- Marketplace health score
- Employer: views/saves/applies
- Apply quality score
- Source performance
- Campaign ROI
- Employer response SLA
- Candidate drop-off analytics
- Comparative benchmarks
- Sponsored vs organic performance
- Review sentiment trend
- Recruiter responsiveness analytics
"""
from datetime import timedelta, date
from collections import defaultdict

from django.db.models import Count, Avg, Sum, Q, F
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    MarketplaceLiquiditySnapshot,
    FunnelEvent,
    EmployerROISummary,
    MarketplaceHealthScore,
)


def _days_ago(n):
    return timezone.now() - timedelta(days=n)


def _pct(num, den):
    return round(num / den * 100, 1) if den else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 16 — Marketplace Analytics
# ─────────────────────────────────────────────────────────────────────────────

class SupplyDemandDashboardView(APIView):
    """
    GET /mktanalytics/supply-demand/
    Job supply vs candidate demand by category and district for the last N days.
    Query params: days=30, category_id, district_id
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        cat_id = request.query_params.get("category_id")
        dist_id = request.query_params.get("district_id")

        qs = MarketplaceLiquiditySnapshot.objects.filter(
            date__gte=_days_ago(days).date()
        ).select_related("category", "district").order_by("-demand_supply_ratio")

        if cat_id:
            qs = qs.filter(category_id=cat_id)
        if dist_id:
            qs = qs.filter(district_id=dist_id)

        segments = list(qs[:100])

        # Summary metrics
        total_active_jobs = sum(s.active_jobs for s in segments)
        total_searches = sum(s.seeker_searches for s in segments)
        total_applies = sum(s.apply_count for s in segments)

        # Under-supplied segments (ratio > 1.5)
        under_supplied = [s for s in segments if s.demand_supply_ratio >= 1.5]
        # Over-supplied (ratio < 0.5)
        over_supplied = [s for s in segments if s.demand_supply_ratio < 0.5]

        return Response({
            "period_days": days,
            "summary": {
                "total_active_jobs": total_active_jobs,
                "total_candidate_searches": total_searches,
                "total_applications": total_applies,
                "search_to_apply_rate_pct": _pct(total_applies, total_searches),
                "avg_demand_supply_ratio": round(
                    sum(s.demand_supply_ratio for s in segments) / len(segments), 2
                ) if segments else None,
            },
            "under_supplied_segments": [
                {
                    "category": s.category.name,
                    "district": s.district.name if s.district else "All",
                    "active_jobs": s.active_jobs,
                    "searches": s.seeker_searches,
                    "ratio": round(s.demand_supply_ratio, 2),
                    "avg_time_to_fill_days": s.avg_time_to_fill_days,
                }
                for s in under_supplied[:10]
            ],
            "over_supplied_segments": [
                {
                    "category": s.category.name,
                    "district": s.district.name if s.district else "All",
                    "active_jobs": s.active_jobs,
                    "searches": s.seeker_searches,
                    "ratio": round(s.demand_supply_ratio, 2),
                }
                for s in over_supplied[:10]
            ],
            "all_segments": [
                {
                    "date": str(s.date),
                    "category": s.category.name,
                    "district": s.district.name if s.district else "All",
                    "active_jobs": s.active_jobs,
                    "seeker_searches": s.seeker_searches,
                    "apply_count": s.apply_count,
                    "ratio": round(s.demand_supply_ratio, 2),
                }
                for s in segments[:50]
            ],
        })


class ConversionFunnelView(APIView):
    """
    GET /mktanalytics/funnel/
    Conversion funnel: search → view → save → apply_start → apply_submit.
    Broken down by page_type and source_channel.
    Query params: days=30, page_type, source_channel
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        page_type = request.query_params.get("page_type")
        source = request.query_params.get("source_channel")

        qs = FunnelEvent.objects.filter(created_at__gte=_days_ago(days))
        if page_type:
            qs = qs.filter(page_type=page_type)
        if source:
            qs = qs.filter(source_channel=source)

        step_counts = dict(qs.values("step").annotate(n=Count("id")).values_list("step", "n"))

        search = step_counts.get("search", 0)
        view = step_counts.get("job_view", 0)
        save = step_counts.get("job_save", 0)
        start = step_counts.get("apply_start", 0)
        submit = step_counts.get("apply_submit", 0)
        company_view = step_counts.get("company_view", 0)
        alert_open = step_counts.get("alert_open", 0)
        alert_click = step_counts.get("alert_click", 0)

        funnel = [
            {"step": "Search", "count": search, "drop_off_pct": None},
            {"step": "Job View", "count": view, "drop_off_pct": _pct(search - view, search) if search else None},
            {"step": "Job Save", "count": save, "drop_off_pct": _pct(view - save, view) if view else None},
            {"step": "Apply Start", "count": start, "drop_off_pct": _pct(view - start, view) if view else None},
            {"step": "Apply Submit", "count": submit, "drop_off_pct": _pct(start - submit, start) if start else None},
        ]

        # By source channel
        by_source = list(
            qs.filter(step="apply_submit")
            .values("source_channel")
            .annotate(applies=Count("id"))
            .order_by("-applies")
        )

        # By page type
        by_page = list(
            qs.values("page_type")
            .annotate(events=Count("id"))
            .order_by("-events")[:10]
        )

        return Response({
            "period_days": days,
            "funnel": funnel,
            "key_rates": {
                "search_to_view_pct": _pct(view, search),
                "view_to_apply_start_pct": _pct(start, view),
                "apply_completion_rate_pct": _pct(submit, start),
                "search_to_apply_pct": _pct(submit, search),
                "alert_open_rate_pct": _pct(alert_open, search),
                "alert_click_to_apply_pct": _pct(submit, alert_click) if alert_click else 0,
                "company_page_views": company_view,
            },
            "by_source_channel": by_source,
            "by_page_type": by_page,
        })


class AlertEngagementView(APIView):
    """
    GET /mktanalytics/alert-engagement/
    Job alert open/click/apply metrics.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        qs = FunnelEvent.objects.filter(created_at__gte=_days_ago(days))

        total_sent = qs.filter(step="search", source_channel="alert").count()
        opens = qs.filter(step="alert_open").count()
        clicks = qs.filter(step="alert_click").count()
        applies = qs.filter(step="apply_submit", source_channel="alert").count()

        from apps.retention_growth.models import DigestQueue
        digests = DigestQueue.objects.filter(created_at__gte=_days_ago(days))
        digest_sent = digests.filter(is_sent=True).count()
        digest_opened = digests.filter(opened_at__isnull=False).count()
        digest_clicked = digests.filter(clicked_job_id__isnull=False).count()

        return Response({
            "period_days": days,
            "job_alerts": {
                "total_alerts_triggered": total_sent,
                "opens": opens,
                "open_rate_pct": _pct(opens, total_sent),
                "clicks": clicks,
                "click_rate_pct": _pct(clicks, opens),
                "applies": applies,
                "alert_to_apply_pct": _pct(applies, clicks),
            },
            "digest_email": {
                "total_sent": digest_sent,
                "opened": digest_opened,
                "open_rate_pct": _pct(digest_opened, digest_sent),
                "clicked": digest_clicked,
                "click_rate_pct": _pct(digest_clicked, digest_opened),
            },
        })


class FraudAbuseDashboardView(APIView):
    """
    GET /mktanalytics/fraud-dashboard/
    Fraud and abuse: flagged jobs, scam patterns, strike rates, duplicate rates.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        since = _days_ago(days)

        from apps.trust_ops.models import ScamAlert, StrikeRecord, SuspensionRecord
        from apps.moderation.models import Report
        from apps.job_quality.models import JobQualityScore, DuplicateJobGroup

        scam_alerts = ScamAlert.objects.filter(created_at__gte=since)
        total_scam = scam_alerts.count()
        resolved_scam = scam_alerts.filter(is_resolved=True).count()

        strikes = StrikeRecord.objects.filter(created_at__gte=since).count()
        suspensions = SuspensionRecord.objects.filter(started_at__gte=since).count()

        reports = Report.objects.filter(created_at__gte=since)
        total_reports = reports.count()
        by_reason = list(reports.values("reason").annotate(n=Count("id")).order_by("-n")[:10])

        # Quality scores
        qs = JobQualityScore.objects.all()
        total_scored = qs.count()
        high_risk = qs.filter(scam_risk__in=["high", "flagged"]).count()
        duplicates = qs.filter(is_duplicate=True).count()
        dup_groups = DuplicateJobGroup.objects.filter(created_at__gte=since, is_resolved=False).count()

        # Latest health score
        latest_health = (
            MarketplaceHealthScore.objects.order_by("-date").values(
                "overall_score", "fraud_rate", "duplicate_rate", "date"
            ).first()
        )

        return Response({
            "period_days": days,
            "scam_alerts": {
                "total": total_scam,
                "resolved": resolved_scam,
                "active": total_scam - resolved_scam,
                "resolution_rate_pct": _pct(resolved_scam, total_scam),
            },
            "strikes_and_suspensions": {
                "new_strikes": strikes,
                "new_suspensions": suspensions,
            },
            "reports": {
                "total": total_reports,
                "by_reason": by_reason,
            },
            "job_quality": {
                "total_scored_jobs": total_scored,
                "high_risk_jobs": high_risk,
                "high_risk_rate_pct": _pct(high_risk, total_scored),
                "duplicate_jobs": duplicates,
                "duplicate_rate_pct": _pct(duplicates, total_scored),
                "open_duplicate_groups": dup_groups,
            },
            "marketplace_health": latest_health,
        })


class CityLiquidityDashboardView(APIView):
    """
    GET /mktanalytics/city-liquidity/
    Liquidity (supply vs demand) broken down by city/district.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))

        qs = (
            MarketplaceLiquiditySnapshot.objects.filter(date__gte=_days_ago(days).date())
            .values("district__name", "district_id")
            .annotate(
                total_jobs=Sum("active_jobs"),
                total_searches=Sum("seeker_searches"),
                total_applies=Sum("apply_count"),
                avg_ratio=Avg("demand_supply_ratio"),
            )
            .order_by("-total_searches")
        )

        cities = [
            {
                "district": r["district__name"] or "Unknown",
                "total_jobs": r["total_jobs"],
                "total_searches": r["total_searches"],
                "total_applies": r["total_applies"],
                "avg_demand_supply_ratio": round(r["avg_ratio"] or 0, 2),
                "search_to_apply_pct": _pct(r["total_applies"], r["total_searches"]),
                "status": (
                    "under_supplied" if (r["avg_ratio"] or 0) > 1.5
                    else "balanced" if (r["avg_ratio"] or 0) >= 0.7
                    else "over_supplied"
                ),
            }
            for r in qs[:50]
        ]

        return Response({
            "period_days": days,
            "cities": cities,
            "note": "Ratio > 1.5 = more seekers than jobs (under-supplied); < 0.5 = over-supplied",
        })


class CohortRetentionView(APIView):
    """
    GET /mktanalytics/cohort-retention/
    Weekly cohort retention — % of users who applied in week N and returned in week N+k.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.applications.models import Application

        weeks = int(request.query_params.get("weeks", 8))
        today = date.today()

        cohorts = []
        for w in range(weeks, 0, -1):
            week_start = today - timedelta(weeks=w)
            week_end = week_start + timedelta(days=7)
            cohort_users = set(
                Application.objects.filter(
                    applied_at__date__gte=week_start,
                    applied_at__date__lt=week_end,
                ).values_list("applicant_id", flat=True)
            )
            if not cohort_users:
                continue

            retention = []
            for offset in range(1, min(w, weeks - w + 1) + 1):
                ret_start = week_start + timedelta(weeks=offset)
                ret_end = ret_start + timedelta(days=7)
                returned = Application.objects.filter(
                    applicant_id__in=cohort_users,
                    applied_at__date__gte=ret_start,
                    applied_at__date__lt=ret_end,
                ).values("applicant_id").distinct().count()
                retention.append({
                    "week_offset": offset,
                    "returned_users": returned,
                    "retention_pct": _pct(returned, len(cohort_users)),
                })

            cohorts.append({
                "cohort_week": str(week_start),
                "cohort_size": len(cohort_users),
                "retention": retention,
            })

        return Response({
            "analysis_weeks": weeks,
            "cohorts": cohorts,
            "explanation": "Each cohort = users who submitted an application in that week. Retention = % who applied again in subsequent weeks.",
        })


class LTVByEmployerTypeView(APIView):
    """
    GET /mktanalytics/ltv/
    Lifetime value proxy by employer type: total spend, jobs posted, applications generated.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.employers.models import EmployerAccount

        employer_types = EmployerAccount.objects.values("employer_type").distinct()
        results = []

        for et in employer_types:
            emp_type = et["employer_type"]
            employers = EmployerAccount.objects.filter(employer_type=emp_type)
            employer_ids = list(employers.values_list("id", flat=True))

            roi_data = EmployerROISummary.objects.filter(employer_id__in=employer_ids).aggregate(
                total_spend=Sum("sponsored_spend_lkr"),
                total_jobs_views=Sum("job_views"),
                total_applications=Sum("applications"),
                total_hired=Sum("hired"),
                avg_quality=Avg("applications_quality_score"),
            )

            results.append({
                "employer_type": emp_type,
                "employer_count": len(employer_ids),
                "total_sponsored_spend_lkr": float(roi_data["total_spend"] or 0),
                "total_job_views": roi_data["total_jobs_views"] or 0,
                "total_applications_generated": roi_data["total_applications"] or 0,
                "total_hired": roi_data["total_hired"] or 0,
                "avg_applicant_quality_score": round(roi_data["avg_quality"] or 0, 1),
                "ltv_proxy_lkr": float(roi_data["total_spend"] or 0),
                "cost_per_hire": round(
                    float(roi_data["total_spend"] or 0) / roi_data["total_hired"]
                    if roi_data["total_hired"] else 0, 2
                ),
            })

        return Response({
            "ltv_by_employer_type": sorted(results, key=lambda x: x["ltv_proxy_lkr"], reverse=True),
            "note": "LTV proxy = total sponsored spend. Cost per hire = total spend / total hired.",
        })


class CACByChannelView(APIView):
    """
    GET /mktanalytics/cac/
    Customer acquisition cost breakdown by channel (organic/direct/promoted/alert/referral).
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 90))

        from apps.promotions_ads.models import AdCampaign

        # Applies by source channel
        by_channel = list(
            FunnelEvent.objects.filter(
                step="apply_submit",
                created_at__gte=_days_ago(days),
            ).values("source_channel")
            .annotate(applies=Count("id"))
            .order_by("-applies")
        )

        # Sponsored spend
        total_spend = (
            EmployerROISummary.objects.filter(
                week_start__gte=(_days_ago(days)).date(),
            ).aggregate(s=Sum("sponsored_spend_lkr"))["s"] or 0
        )
        sponsored_applies = sum(
            r["applies"] for r in by_channel if r["source_channel"] == "promoted"
        )

        results = []
        for ch in by_channel:
            spend = float(total_spend) if ch["source_channel"] == "promoted" else 0
            cac = round(spend / ch["applies"], 2) if ch["applies"] and spend else None
            results.append({
                "channel": ch["source_channel"] or "unknown",
                "applies": ch["applies"],
                "estimated_spend_lkr": spend,
                "cac_lkr": cac,
            })

        return Response({
            "period_days": days,
            "by_channel": results,
            "total_sponsored_spend_lkr": float(total_spend),
            "sponsored_applies": sponsored_applies,
            "note": "CAC calculated only for paid/promoted channels where spend data available.",
        })


class CandidateEngagementScoringView(APIView):
    """
    GET /mktanalytics/candidate-engagement/
    Aggregate candidate-side engagement scoring for marketplace health monitoring.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))

        from apps.applications.models import Application
        from apps.jobs.models import SavedJob
        from apps.analytics.models import SearchLog

        searches = SearchLog.objects.filter(created_at__gte=_days_ago(days))
        total_searches = searches.count()
        searches_with_click = searches.filter(clicked_job_id__isnull=False).count()

        applications = Application.objects.filter(applied_at__gte=_days_ago(days))
        total_applies = applications.count()

        saves = SavedJob.objects.filter(saved_at__gte=_days_ago(days)).count() if hasattr(SavedJob, 'saved_at') else 0

        funnel_qs = FunnelEvent.objects.filter(created_at__gte=_days_ago(days))

        # Daily active applying users
        daily_appliers = applications.values(
            date=TruncDate("applied_at")
        ).annotate(n=Count("applicant_id", distinct=True)).order_by("date")

        return Response({
            "period_days": days,
            "engagement_summary": {
                "total_searches": total_searches,
                "searches_with_job_click": searches_with_click,
                "click_through_rate_pct": _pct(searches_with_click, total_searches),
                "total_applications": total_applies,
                "total_saves": saves,
                "search_to_apply_rate_pct": _pct(total_applies, total_searches),
            },
            "daily_active_appliers": list(
                {"date": str(r["date"]), "appliers": r["n"]}
                for r in daily_appliers
            ),
            "engagement_score": min(100, round(
                _pct(searches_with_click, total_searches) * 0.3
                + _pct(total_applies, total_searches) * 0.5
                + (_pct(saves, total_searches) if saves else 0) * 0.2
            )),
        })


class MarketplaceHealthDashboardView(APIView):
    """
    GET /mktanalytics/health-dashboard/
    Current marketplace health score with trend and component breakdown.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        latest = list(
            MarketplaceHealthScore.objects.order_by("-date").values(
                "date", "overall_score", "job_supply_score", "seeker_demand_score",
                "apply_conversion_score", "employer_response_score",
                "trust_score", "fraud_rate", "duplicate_rate", "avg_apply_rate",
            )[:30]
        )

        if not latest:
            return Response({"detail": "No health data yet."}, status=404)

        current = latest[0]
        prev = latest[1] if len(latest) > 1 else None

        trend = None
        if prev:
            delta = round(current["overall_score"] - prev["overall_score"], 1)
            trend = {"delta": delta, "direction": "up" if delta > 0 else "down" if delta < 0 else "flat"}

        components = [
            {"name": "Job Supply", "score": current["job_supply_score"], "weight": "25%"},
            {"name": "Seeker Demand", "score": current["seeker_demand_score"], "weight": "25%"},
            {"name": "Apply Conversion", "score": current["apply_conversion_score"], "weight": "20%"},
            {"name": "Employer Response", "score": current["employer_response_score"], "weight": "15%"},
            {"name": "Trust & Safety", "score": current["trust_score"], "weight": "15%"},
        ]

        label = (
            "Excellent" if current["overall_score"] >= 80
            else "Good" if current["overall_score"] >= 65
            else "Fair" if current["overall_score"] >= 50
            else "Needs attention"
        )

        return Response({
            "current": {
                "date": str(current["date"]),
                "overall_score": current["overall_score"],
                "label": label,
                "trend": trend,
                "fraud_rate_pct": current["fraud_rate"],
                "duplicate_rate_pct": current["duplicate_rate"],
                "avg_apply_rate_pct": current["avg_apply_rate"],
            },
            "components": components,
            "history": list(reversed([
                {"date": str(r["date"]), "score": r["overall_score"]}
                for r in latest
            ])),
        })


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 17 — Employer Analytics & ROI
# ─────────────────────────────────────────────────────────────────────────────

class EmployerROIDashboardView(APIView):
    """
    GET /mktanalytics/employer/roi/
    Full employer ROI dashboard: views/saves/applies, quality score, trends.
    Employer sees their own data; admin can pass ?employer_id=
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_employer(self, request):
        from apps.employers.models import EmployerAccount
        if request.user.is_staff and request.query_params.get("employer_id"):
            return EmployerAccount.objects.get(pk=request.query_params["employer_id"])
        return getattr(request.user, "employer_account", None)

    def get(self, request):
        employer = self._get_employer(request)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=404)

        weeks = int(request.query_params.get("weeks", 8))
        roi_summaries = EmployerROISummary.objects.filter(
            employer=employer
        ).order_by("-week_start")[:weeks]

        summaries = list(roi_summaries)
        if not summaries:
            return Response({"detail": "No ROI data yet. Post a job and receive applications."})

        totals = {
            "job_views": sum(s.job_views for s in summaries),
            "profile_views": sum(s.profile_views for s in summaries),
            "applications": sum(s.applications for s in summaries),
            "shortlisted": sum(s.shortlisted for s in summaries),
            "hired": sum(s.hired for s in summaries),
            "sponsored_spend_lkr": float(sum(s.sponsored_spend_lkr for s in summaries)),
            "organic_applies": sum(s.organic_applies for s in summaries),
            "sponsored_applies": sum(s.sponsored_applies for s in summaries),
        }

        cost_per_hire = round(
            totals["sponsored_spend_lkr"] / totals["hired"]
            if totals["hired"] else 0, 2
        )

        avg_quality = round(sum(s.applications_quality_score for s in summaries) / len(summaries), 1)

        return Response({
            "employer_id": str(employer.id),
            "employer_name": employer.company_name,
            "period_weeks": weeks,
            "totals": totals,
            "rates": {
                "view_to_apply_pct": _pct(totals["applications"], totals["job_views"]),
                "apply_to_shortlist_pct": _pct(totals["shortlisted"], totals["applications"]),
                "shortlist_to_hire_pct": _pct(totals["hired"], totals["shortlisted"]),
                "sponsored_apply_share_pct": _pct(totals["sponsored_applies"], totals["applications"]),
            },
            "quality": {
                "avg_applicant_quality_score": avg_quality,
                "quality_label": "High" if avg_quality >= 70 else "Medium" if avg_quality >= 45 else "Low",
                "cost_per_hire_lkr": cost_per_hire,
            },
            "weekly_trend": [
                {
                    "week": str(s.week_start),
                    "views": s.job_views,
                    "applications": s.applications,
                    "quality_score": s.applications_quality_score,
                    "sponsored_spend": float(s.sponsored_spend_lkr),
                }
                for s in reversed(summaries)
            ],
        })


class EmployerJobPerformanceView(APIView):
    """
    GET /mktanalytics/employer/jobs/
    Per-job performance: views, saves, applies, apply quality, sponsored vs organic.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.employers.models import EmployerAccount
        from apps.jobs.models import JobListing
        from apps.applications.models import Application
        from apps.analytics.models import EventLog

        if request.user.is_staff and request.query_params.get("employer_id"):
            employer = EmployerAccount.objects.get(pk=request.query_params["employer_id"])
        else:
            employer = getattr(request.user, "employer_account", None)

        if not employer:
            return Response({"detail": "Employer account not found."}, status=404)

        days = int(request.query_params.get("days", 30))

        jobs = JobListing.objects.filter(employer=employer).order_by("-created_at")[:50]
        job_ids = [j.id for j in jobs]

        # Applications per job
        app_counts = dict(
            Application.objects.filter(job_id__in=job_ids, applied_at__gte=_days_ago(days))
            .values("job_id").annotate(n=Count("id")).values_list("job_id", "n")
        )

        # Funnel events per job
        view_counts = dict(
            FunnelEvent.objects.filter(
                job_id__in=[str(j) for j in job_ids],
                step="job_view",
                created_at__gte=_days_ago(days),
            ).values("job_id").annotate(n=Count("id")).values_list("job_id", "n")
        )

        sponsored_applies = dict(
            FunnelEvent.objects.filter(
                job_id__in=[str(j) for j in job_ids],
                step="apply_submit",
                source_channel="promoted",
                created_at__gte=_days_ago(days),
            ).values("job_id").annotate(n=Count("id")).values_list("job_id", "n")
        )

        results = []
        for job in jobs:
            job_id = job.id
            views = view_counts.get(str(job_id), 0)
            applies = app_counts.get(job_id, 0)
            sp_applies = sponsored_applies.get(str(job_id), 0)
            organic = max(0, applies - sp_applies)

            quality_score = getattr(getattr(job, "quality_score_obj", None), "overall_score", None)

            results.append({
                "job_id": str(job_id),
                "title": job.title,
                "status": job.status,
                "posted_at": job.created_at,
                "views": views,
                "applies": applies,
                "view_to_apply_pct": _pct(applies, views),
                "organic_applies": organic,
                "sponsored_applies": sp_applies,
                "quality_score": round(quality_score, 1) if quality_score else None,
                "is_sponsored": getattr(job, "is_sponsored", False),
            })

        return Response({
            "employer_name": employer.company_name,
            "period_days": days,
            "jobs": sorted(results, key=lambda x: x["applies"], reverse=True),
        })


class EmployerSourcePerformanceView(APIView):
    """
    GET /mktanalytics/employer/sources/
    Application source performance: organic, promoted, alert, direct, referral.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.employers.models import EmployerAccount
        from apps.jobs.models import JobListing

        employer = getattr(request.user, "employer_account", None)
        if not employer and request.user.is_staff:
            emp_id = request.query_params.get("employer_id")
            employer = EmployerAccount.objects.get(pk=emp_id) if emp_id else None

        if not employer:
            return Response({"detail": "Employer account not found."}, status=404)

        days = int(request.query_params.get("days", 30))
        job_ids = list(
            JobListing.objects.filter(employer=employer).values_list("id", flat=True)
        )
        job_id_strs = [str(j) for j in job_ids]

        sources = list(
            FunnelEvent.objects.filter(
                job_id__in=job_id_strs,
                step="apply_submit",
                created_at__gte=_days_ago(days),
            ).values("source_channel")
            .annotate(applies=Count("id"))
            .order_by("-applies")
        )

        total = sum(s["applies"] for s in sources)
        return Response({
            "period_days": days,
            "total_applications": total,
            "by_source": [
                {
                    "source": s["source_channel"] or "unknown",
                    "applies": s["applies"],
                    "share_pct": _pct(s["applies"], total),
                }
                for s in sources
            ],
            "best_source": sources[0]["source_channel"] if sources else None,
        })


class EmployerResponseSLAView(APIView):
    """
    GET /mktanalytics/employer/response-sla/
    Employer response time analytics: avg response hours, SLA compliance, unresponded.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.employers.models import EmployerAccount
        from apps.messaging.models import MessageThread, Message

        employer = getattr(request.user, "employer_account", None)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=404)

        days = int(request.query_params.get("days", 30))
        threads = MessageThread.objects.filter(
            participant_one=employer.user if hasattr(employer, "user") else request.user,
            created_at__gte=_days_ago(days),
        ).prefetch_related("messages")

        sla_target_hours = 48
        response_times = []
        unresponded = 0

        for t in threads:
            msgs = list(t.messages.order_by("created_at"))
            employer_user_id = request.user.id
            replied = False
            for i, msg in enumerate(msgs):
                if msg.sender_id == employer_user_id and i > 0:
                    prev = msgs[i - 1]
                    if prev.sender_id != employer_user_id:
                        delta_h = (msg.created_at - prev.created_at).total_seconds() / 3600
                        response_times.append(delta_h)
                        replied = True
                        break
            if not replied:
                unresponded += 1

        avg_resp = round(sum(response_times) / len(response_times), 1) if response_times else None
        within_sla = sum(1 for h in response_times if h <= sla_target_hours)

        return Response({
            "period_days": days,
            "sla_target_hours": sla_target_hours,
            "total_threads": threads.count(),
            "responded_threads": len(response_times),
            "unresponded_threads": unresponded,
            "avg_response_time_hours": avg_resp,
            "within_sla_count": within_sla,
            "sla_compliance_pct": _pct(within_sla, len(response_times)),
            "response_speed_label": (
                "Excellent" if avg_resp and avg_resp <= 4
                else "Good" if avg_resp and avg_resp <= 24
                else "Needs improvement" if avg_resp
                else "No data"
            ),
            "tips": [
                "Maintain a < 24h response time to improve candidate experience.",
                "Use message templates to respond faster.",
                "Set up mobile push notifications to respond on the go.",
            ],
        })


class CandidateDropOffAnalyticsView(APIView):
    """
    GET /mktanalytics/employer/drop-off/
    Where candidates drop off in the employer's apply funnel.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.employers.models import EmployerAccount
        from apps.jobs.models import JobListing

        employer = getattr(request.user, "employer_account", None)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=404)

        days = int(request.query_params.get("days", 30))
        job_ids = [str(j) for j in JobListing.objects.filter(employer=employer).values_list("id", flat=True)]

        step_order = ["job_view", "apply_start", "apply_submit"]
        counts = {}
        for step in step_order:
            counts[step] = FunnelEvent.objects.filter(
                job_id__in=job_ids,
                step=step,
                created_at__gte=_days_ago(days),
            ).count()

        view = counts.get("job_view", 0)
        start = counts.get("apply_start", 0)
        submit = counts.get("apply_submit", 0)

        stages = [
            {"stage": "Job View", "count": view, "drop_off_pct": None},
            {"stage": "Apply Clicked", "count": start, "drop_off_pct": _pct(view - start, view)},
            {"stage": "Application Submitted", "count": submit, "drop_off_pct": _pct(start - submit, start)},
        ]

        biggest_drop = max(stages[1:], key=lambda s: s["drop_off_pct"] or 0)
        suggestions = {
            "Apply Clicked": "Improve job page CTA clarity and reduce required fields in the apply form.",
            "Application Submitted": "Simplify and shorten your application form — too many steps cause abandonment.",
        }

        return Response({
            "period_days": days,
            "funnel": stages,
            "view_to_apply_rate_pct": _pct(submit, view),
            "completion_rate_pct": _pct(submit, start),
            "biggest_drop_stage": biggest_drop["stage"],
            "suggestion": suggestions.get(biggest_drop["stage"], "Review funnel data regularly."),
        })


class EmployerComparativeBenchmarkView(APIView):
    """
    GET /mktanalytics/employer/benchmark/
    Compare employer's performance vs platform averages.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.employers.models import EmployerAccount

        employer = getattr(request.user, "employer_account", None)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=404)

        weeks = int(request.query_params.get("weeks", 4))

        # Employer's own metrics
        my_summaries = EmployerROISummary.objects.filter(
            employer=employer, week_start__gte=(_days_ago(weeks * 7)).date()
        )
        my_totals = my_summaries.aggregate(
            views=Sum("job_views"), apps=Sum("applications"),
            quality=Avg("applications_quality_score"), hired=Sum("hired"),
        )

        # Platform averages (across all employers in same period)
        all_summaries = EmployerROISummary.objects.filter(
            week_start__gte=(_days_ago(weeks * 7)).date()
        )
        all_totals = all_summaries.aggregate(
            avg_views=Avg("job_views"), avg_apps=Avg("applications"),
            avg_quality=Avg("applications_quality_score"), avg_hired=Avg("hired"),
        )

        def vs(my_val, avg_val, label, higher_better=True):
            if my_val is None or avg_val is None:
                return {"metric": label, "mine": my_val, "platform_avg": avg_val, "status": "no_data"}
            diff = round(my_val - avg_val, 1)
            pct_diff = round((diff / avg_val) * 100, 1) if avg_val else 0
            better = diff > 0 if higher_better else diff < 0
            return {
                "metric": label,
                "mine": round(my_val, 1),
                "platform_avg": round(avg_val, 1),
                "pct_vs_avg": pct_diff,
                "status": "above_avg" if better else "below_avg" if not better else "at_avg",
            }

        return Response({
            "period_weeks": weeks,
            "employer": employer.company_name,
            "benchmarks": [
                vs(my_totals["views"] or 0, all_totals["avg_views"] or 0, "Job Views (total)"),
                vs(my_totals["apps"] or 0, all_totals["avg_apps"] or 0, "Applications (total)"),
                vs(my_totals["quality"] or 0, all_totals["avg_quality"] or 0, "Applicant Quality Score"),
                vs(my_totals["hired"] or 0, all_totals["avg_hired"] or 0, "Hires"),
            ],
        })


class ReviewSentimentTrendView(APIView):
    """
    GET /mktanalytics/employer/review-sentiment/
    Weekly trend of review ratings and sentiment signals for this employer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.employers.models import EmployerAccount
        from apps.reviews.models import CompanyReview

        employer = getattr(request.user, "employer_account", None)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=404)

        weeks = int(request.query_params.get("weeks", 12))

        weekly = list(
            CompanyReview.objects.filter(
                employer=employer,
                status="approved",
                created_at__gte=_days_ago(weeks * 7),
            ).annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(
                count=Count("id"),
                avg_rating=Avg("overall_rating"),
                avg_wlb=Avg("work_life_balance"),
                avg_growth=Avg("career_growth"),
                avg_mgmt=Avg("management"),
            )
            .order_by("week")
        )

        recent_reviews = CompanyReview.objects.filter(
            employer=employer, status="approved"
        ).order_by("-created_at")[:5]

        total = CompanyReview.objects.filter(employer=employer, status="approved").count()
        overall = CompanyReview.objects.filter(
            employer=employer, status="approved"
        ).aggregate(avg=Avg("overall_rating"))["avg"] or 0

        sentiment_label = "Positive" if overall >= 4.0 else "Neutral" if overall >= 3.0 else "Negative"

        return Response({
            "period_weeks": weeks,
            "summary": {
                "total_reviews": total,
                "avg_rating": round(overall, 2),
                "sentiment_label": sentiment_label,
                "recommended_by_pct": _pct(
                    CompanyReview.objects.filter(employer=employer, status="approved", would_recommend=True).count(),
                    total,
                ),
            },
            "weekly_trend": [
                {
                    "week": str(r["week"].date()) if r["week"] else None,
                    "reviews": r["count"],
                    "avg_rating": round(r["avg_rating"] or 0, 2),
                    "avg_work_life_balance": round(r["avg_wlb"] or 0, 2),
                    "avg_career_growth": round(r["avg_growth"] or 0, 2),
                    "avg_management": round(r["avg_mgmt"] or 0, 2),
                }
                for r in weekly
            ],
            "recent_reviews": [
                {
                    "id": str(r.id),
                    "rating": r.overall_rating,
                    "title": r.title,
                    "relationship": r.relationship,
                    "date": r.created_at.date(),
                }
                for r in recent_reviews
            ],
        })
