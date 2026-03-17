"""
Feature 8 — Salary Intelligence & Compensation Marketplace
Extra views: salary guide by title+location, pay transparency score, total comp tool,
hourly/salaried conversion, comp comparison, pay by experience/skill/certification,
pay ranges by employer, salary confidence score, cost-of-living overlay, verified submissions.
"""
from django.db.models import Avg, Count, Min, Max, Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from .models import SalaryEstimate, SalaryBenchmark, SalaryTrend, CostOfLivingIndex, SalarySubmission


# ── Salary Guide Page ─────────────────────────────────────────────────────────

class SalaryGuideView(APIView):
    """
    GET /salary-intelligence/guide/?title=<str>&district=<id>&experience_level=<str>
    Full salary guide page data: estimates, trend, COL overlay, experience breakdown.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        title = request.query_params.get("title", "").strip()
        district_id = request.query_params.get("district")
        exp_level = request.query_params.get("experience_level", "")

        if not title:
            return Response({"detail": "title query param required."}, status=400)

        # Find best matching estimate
        qs = SalaryEstimate.objects.filter(normalized_title__icontains=title)
        if district_id:
            qs = qs.filter(district_id=district_id)
        if exp_level:
            qs = qs.filter(Q(experience_level=exp_level) | Q(experience_level=""))

        estimate = qs.order_by("-confidence_score", "-sample_size").first()

        # Experience breakdown (all levels for this title)
        exp_breakdown = list(
            SalaryEstimate.objects.filter(
                normalized_title__icontains=title,
                experience_level__in=["entry", "mid", "senior", "lead", "director"],
            ).filter(
                Q(district_id=district_id) if district_id else Q()
            ).values("experience_level", "salary_median_lkr", "salary_p25_lkr", "salary_p75_lkr", "confidence_score")
        )

        # Trend data (last 12 months)
        trend_qs = SalaryTrend.objects.filter(normalized_title__icontains=title)
        if district_id:
            trend_qs = trend_qs.filter(district_id=district_id)
        trends = list(trend_qs.order_by("month")[:12].values("month", "median_salary_lkr", "sample_size"))

        # COL overlay
        col = None
        if district_id:
            try:
                col_obj = CostOfLivingIndex.objects.get(district_id=district_id)
                col = {
                    "index_value": col_obj.index_value,
                    "housing_index": col_obj.housing_index,
                    "transport_index": col_obj.transport_index,
                    "food_index": col_obj.food_index,
                }
            except CostOfLivingIndex.DoesNotExist:
                pass

        # COL-adjusted salary
        col_adjusted = None
        if estimate and col and estimate.salary_median_lkr:
            # Adjust for district cost relative to national base
            adjustment = 100 / col["index_value"]
            col_adjusted = int(estimate.salary_median_lkr * adjustment)

        return Response({
            "query": {"title": title, "district": district_id, "experience_level": exp_level},
            "estimate": {
                "salary_p10": estimate.salary_p10_lkr,
                "salary_p25": estimate.salary_p25_lkr,
                "salary_median": estimate.salary_median_lkr,
                "salary_p75": estimate.salary_p75_lkr,
                "salary_p90": estimate.salary_p90_lkr,
                "sample_size": estimate.sample_size,
                "confidence_score": estimate.confidence_score,
                "confidence_label": (
                    "High Confidence" if estimate.confidence_score >= 0.7
                    else "Moderate Confidence" if estimate.confidence_score >= 0.4
                    else "Estimated"
                ),
                "currency": estimate.currency,
                "salary_period": estimate.salary_period,
                "calculated_at": estimate.calculated_at,
            } if estimate else None,
            "experience_breakdown": exp_breakdown,
            "trend": trends,
            "cost_of_living": col,
            "col_adjusted_median": col_adjusted,
            "hourly_equivalent": round(estimate.salary_median_lkr / 176, 0) if estimate and estimate.salary_median_lkr else None,  # 22 days × 8 hrs
        })


# ── Pay Transparency Score by Employer ───────────────────────────────────────

class PayTransparencyScoreView(APIView):
    """
    GET /salary-intelligence/transparency/<slug>/
    How transparent an employer is about pay based on job postings + submissions.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        from apps.jobs.models import JobListing
        from apps.employers.models import EmployerAccount
        try:
            employer = EmployerAccount.objects.get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response(status=404)

        total_jobs = JobListing.objects.filter(employer=employer, status="active").count()
        jobs_with_salary = JobListing.objects.filter(
            employer=employer, status="active",
            salary_min__isnull=False,
        ).count()

        verified_submissions = SalarySubmission.objects.filter(
            employer=employer,
            verification_status="verified",
        ).count()

        transparency_pct = round(jobs_with_salary / total_jobs * 100, 1) if total_jobs else 0
        score = min(100, round(transparency_pct * 0.6 + min(verified_submissions * 5, 40)))

        return Response({
            "employer_slug": slug,
            "employer_name": employer.company_name,
            "total_active_jobs": total_jobs,
            "jobs_showing_salary": jobs_with_salary,
            "salary_transparency_pct": transparency_pct,
            "verified_salary_submissions": verified_submissions,
            "pay_transparency_score": score,
            "label": (
                "Highly Transparent" if score >= 80
                else "Transparent" if score >= 60
                else "Partially Transparent" if score >= 30
                else "Low Transparency"
            ),
        })


# ── Company-Specific Salary Page ──────────────────────────────────────────────

class CompanySalaryPageView(APIView):
    """
    GET /salary-intelligence/company/<slug>/salaries/?title=<str>
    Aggregated verified salary data for a specific employer.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        title = request.query_params.get("title", "")
        qs = SalarySubmission.objects.filter(
            employer__slug=slug,
            verification_status="verified",
        )
        if title:
            qs = qs.filter(normalized_title__icontains=title)

        agg = qs.aggregate(
            count=Count("id"),
            avg_base=Avg("base_salary_lkr"),
            avg_total=Avg("total_comp_lkr"),
            min_base=Min("base_salary_lkr"),
            max_base=Max("base_salary_lkr"),
        )

        # Breakdown by experience level
        by_level = list(
            qs.values("experience_level")
            .annotate(count=Count("id"), avg=Avg("base_salary_lkr"))
            .order_by("experience_level")
        )

        # Breakdown by job type
        by_type = list(
            qs.values("job_type")
            .annotate(count=Count("id"), avg=Avg("base_salary_lkr"))
        )

        return Response({
            "employer_slug": slug,
            "filter_title": title or None,
            "verified_submissions": agg["count"] or 0,
            "avg_base_salary": round(agg["avg_base"] or 0),
            "avg_total_comp": round(agg["avg_total"] or 0),
            "salary_range": {"min": agg["min_base"], "max": agg["max_base"]},
            "by_experience_level": by_level,
            "by_job_type": by_type,
        })


# ── Total Compensation Tool ───────────────────────────────────────────────────

class TotalCompensationView(APIView):
    """
    POST /salary-intelligence/total-comp/
    Calculates total compensation value from base + benefits inputs.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        base = request.data.get("base_salary_lkr", 0)
        bonus_pct = request.data.get("bonus_pct", 0)        # % of base
        medical = request.data.get("medical_value_lkr", 0)
        transport = request.data.get("transport_value_lkr", 0)
        meal = request.data.get("meal_value_lkr", 0)
        other_benefits = request.data.get("other_benefits_lkr", 0)
        equity_annual = request.data.get("equity_value_lkr", 0)

        bonus_value = int(float(base) * float(bonus_pct) / 100)
        total_cash = int(float(base)) + bonus_value
        total_comp = total_cash + int(float(medical)) + int(float(transport)) + int(float(meal)) + int(float(other_benefits)) + int(float(equity_annual))

        return Response({
            "base_salary": int(base),
            "bonus_value": bonus_value,
            "total_cash": total_cash,
            "benefits_value": int(float(medical)) + int(float(transport)) + int(float(meal)) + int(float(other_benefits)),
            "equity_value": int(equity_annual),
            "total_compensation": total_comp,
            "hourly_rate_equivalent": round(int(base) / 176, 2),
            "daily_rate_equivalent": round(int(base) / 22, 2),
        })


# ── Compensation Compare Tool ─────────────────────────────────────────────────

class CompensationCompareView(APIView):
    """
    GET /salary-intelligence/compare/?title_a=<str>&title_b=<str>&district_a=<id>&district_b=<id>
    Side-by-side salary comparison for two roles.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        def _fetch(title, district_id):
            qs = SalaryEstimate.objects.filter(normalized_title__icontains=title)
            if district_id:
                qs = qs.filter(district_id=district_id)
            obj = qs.order_by("-confidence_score").first()
            return {
                "title": title,
                "district_id": district_id,
                "salary_median": obj.salary_median_lkr if obj else None,
                "salary_p25": obj.salary_p25_lkr if obj else None,
                "salary_p75": obj.salary_p75_lkr if obj else None,
                "confidence_score": obj.confidence_score if obj else None,
                "sample_size": obj.sample_size if obj else None,
            }

        title_a = request.query_params.get("title_a", "")
        title_b = request.query_params.get("title_b", "")
        district_a = request.query_params.get("district_a")
        district_b = request.query_params.get("district_b")

        if not title_a or not title_b:
            return Response({"detail": "Provide title_a and title_b"}, status=400)

        role_a = _fetch(title_a, district_a)
        role_b = _fetch(title_b, district_b)

        diff = None
        if role_a["salary_median"] and role_b["salary_median"]:
            diff = role_a["salary_median"] - role_b["salary_median"]

        return Response({"role_a": role_a, "role_b": role_b, "median_difference": diff})


# ── Pay by Skills / Certification ─────────────────────────────────────────────

class SkillPayView(APIView):
    """
    GET /salary-intelligence/skill-pay/?skill=<str>
    Salary premium analysis for a skill or certification keyword.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        skill = request.query_params.get("skill", "").strip()
        if not skill:
            return Response({"detail": "skill required."}, status=400)

        from apps.jobs.models import JobListing
        # Jobs mentioning this skill
        with_skill = JobListing.objects.filter(
            status="active",
            required_skills__icontains=skill,
            salary_min__isnull=False,
        ).aggregate(avg=Avg("salary_min"), count=Count("id"), max=Max("salary_max"), min=Min("salary_min"))

        # All active jobs with salary
        all_avg = JobListing.objects.filter(
            status="active", salary_min__isnull=False
        ).aggregate(avg=Avg("salary_min"))

        premium_pct = None
        if with_skill["avg"] and all_avg["avg"]:
            premium_pct = round((with_skill["avg"] - all_avg["avg"]) / all_avg["avg"] * 100, 1)

        return Response({
            "skill": skill,
            "jobs_requiring_skill": with_skill["count"] or 0,
            "avg_salary_with_skill": round(with_skill["avg"] or 0),
            "salary_range": {"min": with_skill["min"], "max": with_skill["max"]},
            "market_avg_salary": round(all_avg["avg"] or 0),
            "skill_salary_premium_pct": premium_pct,
            "label": (
                f"+{premium_pct}% above market average" if premium_pct and premium_pct > 0
                else f"{premium_pct}% vs market average" if premium_pct is not None
                else "Insufficient data"
            ),
        })


# ── Shift/Contract Pay Comparison ─────────────────────────────────────────────

class ShiftPayComparisonView(APIView):
    """GET /salary-intelligence/shift-pay/?title=<str>"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        title = request.query_params.get("title", "")
        from apps.jobs.models import JobListing

        result = {}
        for job_type in ["full_time", "part_time", "contract", "freelance"]:
            agg = JobListing.objects.filter(
                status="active",
                salary_min__isnull=False,
                job_type=job_type,
                **({"title__icontains": title} if title else {}),
            ).aggregate(avg=Avg("salary_min"), count=Count("id"))
            result[job_type] = {"avg_salary": round(agg["avg"] or 0), "count": agg["count"] or 0}

        return Response({"title": title, "by_job_type": result})


# ── Salary Submission (verified) ──────────────────────────────────────────────

class SalarySubmitView(APIView):
    """POST /salary-intelligence/submit/ — submit anonymous salary report."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.employers.models import EmployerAccount
        d = request.data
        employer = None
        if d.get("employer_slug"):
            employer = EmployerAccount.objects.filter(slug=d["employer_slug"]).first()

        sub = SalarySubmission.objects.create(
            employer=employer,
            normalized_title=d.get("title", ""),
            district_id=d.get("district_id"),
            experience_years=d.get("experience_years"),
            experience_level=d.get("experience_level", ""),
            base_salary_lkr=int(d.get("base_salary_lkr", 0)),
            total_comp_lkr=int(d.get("total_comp_lkr", 0)) or None,
            has_bonus=bool(d.get("has_bonus", False)),
            has_medical=bool(d.get("has_medical", False)),
            job_type=d.get("job_type", ""),
            gender=d.get("gender", ""),
            submitted_by=request.user,
        )
        return Response({
            "id": str(sub.id),
            "status": sub.verification_status,
            "message": "Salary report submitted anonymously. Thank you for contributing!",
        }, status=201)
