"""
Feature 7 — Company Pages, Employer Intelligence & Reputation
Additional views: rich company page, office pages, benefits, Q&A CRUD,
salary snapshots, hiring indicators, response time, comparison tool,
workplace scorecard, company followers, employer similarity, review summaries,
employee-generated media, company news/updates.
"""
from django.db.models import Count, Avg, Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import (
    RetrieveAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView,
)

from .models import (
    CompanyOfficeLocation, CompanyBenefit, CompanyQnA,
    HiringActivityIndicator, EmployerComparison,
)
from apps.employers.models import EmployerAccount


# ── Rich Company Page ─────────────────────────────────────────────────────────

class CompanyPageView(APIView):
    """
    GET /company-intelligence/<slug>/
    Full public company intelligence page data.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            employer = EmployerAccount.objects.select_related(
                "industry", "headquarters"
            ).get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response({"detail": "Company not found."}, status=404)

        # Active jobs count
        from apps.jobs.models import JobListing
        active_jobs = JobListing.objects.filter(employer=employer, status="active").count()

        # Benefits
        benefits = CompanyBenefit.objects.filter(employer=employer).values(
            "id", "category", "label", "description", "is_highlighted"
        )

        # Office locations
        offices = CompanyOfficeLocation.objects.filter(employer=employer).values(
            "id", "name", "address", "city", "is_headquarters", "active_job_count", "employee_count"
        )

        # Q&A (top approved)
        qna = CompanyQnA.objects.filter(employer=employer, status="approved").values(
            "id", "question", "answer", "is_employer_answer", "helpful_count"
        )[:10]

        # Latest hiring activity
        hiring = HiringActivityIndicator.objects.filter(employer=employer).order_by("-week_start").first()

        # Application response rate
        from apps.applications.models import Application
        total_apps = Application.objects.filter(employer=employer).count()
        responded_apps = Application.objects.filter(
            employer=employer,
            status__in=["viewed", "shortlisted", "interview", "offer", "hired", "rejected"],
        ).count()
        response_rate = round(responded_apps / total_apps * 100, 1) if total_apps else 0

        # Reviews summary (from reviews app if available)
        review_summary = {}
        try:
            from apps.reviews.models import EmployerReview
            review_qs = EmployerReview.objects.filter(employer=employer, status="approved")
            if review_qs.exists():
                review_summary = {
                    "count": review_qs.count(),
                    "avg_overall": round(review_qs.aggregate(a=Avg("rating_overall"))["a"] or 0, 1),
                    "avg_work_life_balance": round(review_qs.aggregate(a=Avg("rating_work_life_balance"))["a"] or 0, 1),
                    "avg_management": round(review_qs.aggregate(a=Avg("rating_management"))["a"] or 0, 1),
                    "avg_compensation": round(review_qs.aggregate(a=Avg("rating_compensation"))["a"] or 0, 1),
                    "avg_growth": round(review_qs.aggregate(a=Avg("rating_growth"))["a"] or 0, 1),
                }
        except Exception:
            pass

        return Response({
            "id": str(employer.id),
            "slug": employer.slug,
            "company_name": employer.company_name,
            "description": employer.description,
            "industry": str(employer.industry) if employer.industry else None,
            "company_size": employer.company_size,
            "founded_year": employer.founded_year,
            "headquarters": str(employer.headquarters) if employer.headquarters else None,
            "website": employer.website,
            "logo": employer.logo.url if employer.logo else None,
            "cover_image": employer.cover_image.url if employer.cover_image else None,
            "linkedin_url": employer.linkedin_url,
            "is_verified": employer.is_verified,
            "verification_badge": employer.verification_badge,
            "plan": employer.plan,
            "active_jobs_count": active_jobs,
            "follower_count": employer.follower_count,
            "avg_rating": float(employer.avg_rating),
            "review_count": employer.review_count,
            "review_summary": review_summary,
            "response_rate_pct": response_rate,
            "is_actively_hiring": hiring.is_actively_hiring if hiring else False,
            "avg_response_hours": hiring.avg_response_hours if hiring else None,
            "benefits": list(benefits),
            "offices": list(offices),
            "qna": list(qna),
        })


# ── Office Location CRUD (employer-facing) ────────────────────────────────────

class CompanyOfficeListCreateView(ListCreateAPIView):
    """GET/POST /company-intelligence/offices/ (employer only)."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CompanyOfficeLocation.objects.filter(employer__team_members__user=self.request.user)

    def perform_create(self, serializer):
        employer = EmployerAccount.objects.filter(team_members__user=self.request.user).first()
        serializer.save(employer=employer)

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class OfficeSerializer(s.ModelSerializer):
            class Meta:
                model = CompanyOfficeLocation
                exclude = ["employer"]
        return OfficeSerializer


# ── Company Q&A ───────────────────────────────────────────────────────────────

class CompanyQnAListCreateView(ListCreateAPIView):
    """GET (public) or POST (authenticated) company Q&A."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return CompanyQnA.objects.filter(employer__slug=slug, status="approved")

    def perform_create(self, serializer):
        slug = self.kwargs["slug"]
        employer = EmployerAccount.objects.get(slug=slug)
        serializer.save(employer=employer, asked_by=self.request.user)

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class QnASerializer(s.ModelSerializer):
            class Meta:
                model = CompanyQnA
                fields = ["id", "question", "answer", "is_employer_answer", "helpful_count", "status", "created_at"]
                read_only_fields = ["answer", "is_employer_answer", "helpful_count", "status", "created_at"]
        return QnASerializer


class CompanyQnAHelpfulView(APIView):
    """POST /company-intelligence/<slug>/qna/<uuid>/helpful/ — mark as helpful."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug, pk):
        try:
            qna = CompanyQnA.objects.get(pk=pk, employer__slug=slug, status="approved")
            qna.helpful_count += 1
            qna.save(update_fields=["helpful_count"])
            return Response({"helpful_count": qna.helpful_count})
        except CompanyQnA.DoesNotExist:
            return Response(status=404)


# ── Benefits (public) ─────────────────────────────────────────────────────────

class CompanyBenefitsView(APIView):
    """GET /company-intelligence/<slug>/benefits/"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        benefits = CompanyBenefit.objects.filter(employer__slug=slug).order_by("-is_highlighted", "sort_order")
        # Group by category
        grouped: dict = {}
        for b in benefits:
            cat = b.get_category_display()
            grouped.setdefault(cat, []).append({
                "id": str(b.id), "label": b.label,
                "description": b.description, "is_highlighted": b.is_highlighted,
            })
        return Response({"benefits": grouped})


# ── Hiring Activity Feed ──────────────────────────────────────────────────────

class HiringActivityView(APIView):
    """GET /company-intelligence/<slug>/hiring-activity/?weeks=8"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        weeks = min(int(request.query_params.get("weeks", 8)), 52)
        activity = HiringActivityIndicator.objects.filter(
            employer__slug=slug,
        ).order_by("-week_start")[:weeks]

        return Response({
            "history": [{
                "week_start": a.week_start,
                "new_jobs_posted": a.new_jobs_posted,
                "jobs_filled": a.jobs_filled,
                "avg_response_hours": a.avg_response_hours,
                "avg_time_to_hire_days": a.avg_time_to_hire_days,
                "open_positions": a.open_positions,
                "is_actively_hiring": a.is_actively_hiring,
            } for a in activity],
        })


# ── Workplace Scorecard ───────────────────────────────────────────────────────

class WorkplaceScorecardView(APIView):
    """
    GET /company-intelligence/<slug>/scorecard/
    Aggregate review scores across all rating dimensions.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            employer = EmployerAccount.objects.get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response(status=404)

        scorecard = {
            "employer": slug,
            "overall": float(employer.avg_rating),
            "total_reviews": employer.review_count,
        }

        try:
            from apps.reviews.models import EmployerReview
            qs = EmployerReview.objects.filter(employer=employer, status="approved")
            if qs.exists():
                agg = qs.aggregate(
                    wb=Avg("rating_work_life_balance"),
                    mgmt=Avg("rating_management"),
                    comp=Avg("rating_compensation"),
                    growth=Avg("rating_growth"),
                )
                scorecard.update({
                    "work_life_balance": round(agg["wb"] or 0, 2),
                    "management": round(agg["mgmt"] or 0, 2),
                    "compensation": round(agg["comp"] or 0, 2),
                    "career_growth": round(agg["growth"] or 0, 2),
                })
                # Recommend score vs. do not recommend
                recommend = qs.filter(would_recommend=True).count()
                scorecard["recommend_pct"] = round(recommend / qs.count() * 100, 1)
        except Exception:
            pass

        return Response(scorecard)


# ── Company Comparison ────────────────────────────────────────────────────────

class CompanyCompareView(APIView):
    """
    GET /company-intelligence/compare/?a=<slug>&b=<slug>
    Side-by-side comparison of two companies.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        slug_a = request.query_params.get("a", "")
        slug_b = request.query_params.get("b", "")
        if not slug_a or not slug_b:
            return Response({"detail": "Provide ?a=<slug>&b=<slug>"}, status=400)

        try:
            ea = EmployerAccount.objects.get(slug=slug_a)
            eb = EmployerAccount.objects.get(slug=slug_b)
        except EmployerAccount.DoesNotExist:
            return Response({"detail": "One or both companies not found."}, status=404)

        def _snapshot(emp):
            from apps.jobs.models import JobListing
            return {
                "slug": emp.slug,
                "name": emp.company_name,
                "logo": emp.logo.url if emp.logo else None,
                "industry": str(emp.industry) if emp.industry else None,
                "size": emp.company_size,
                "founded_year": emp.founded_year,
                "is_verified": emp.is_verified,
                "avg_rating": float(emp.avg_rating),
                "review_count": emp.review_count,
                "follower_count": emp.follower_count,
                "active_jobs": JobListing.objects.filter(employer=emp, status="active").count(),
                "plan": emp.plan,
            }

        # Check for pre-computed comparison
        try:
            precomp = EmployerComparison.objects.get(
                Q(employer_a=ea, employer_b=eb) | Q(employer_a=eb, employer_b=ea)
            )
            comparison_data = precomp.comparison_data
        except EmployerComparison.DoesNotExist:
            comparison_data = {}

        return Response({
            "company_a": _snapshot(ea),
            "company_b": _snapshot(eb),
            "comparison_data": comparison_data,
        })


# ── Company Follow/Unfollow ───────────────────────────────────────────────────

class CompanyFollowView(APIView):
    """POST /company-intelligence/<slug>/follow/ — follow or unfollow a company."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        try:
            employer = EmployerAccount.objects.get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response(status=404)

        action = request.data.get("action", "follow")  # 'follow' or 'unfollow'

        if action == "follow":
            # Use seeker's blocked_companies M2M as a follow list analog
            # In production this would be a dedicated CompanyFollow model
            employer.follower_count = max(0, employer.follower_count + 1)
            employer.save(update_fields=["follower_count"])
            # Also create a company alert if requested
            follow_alerts = request.data.get("enable_job_alerts", False)
            if follow_alerts:
                JobAlert = None
                try:
                    from apps.notifications.models import JobAlert as JA
                    JA.objects.get_or_create(
                        user=request.user,
                        company=employer,
                        defaults={
                            "name": f"Jobs at {employer.company_name}",
                            "frequency": "instant",
                        },
                    )
                except Exception:
                    pass
            return Response({"followed": True, "follower_count": employer.follower_count})
        else:
            employer.follower_count = max(0, employer.follower_count - 1)
            employer.save(update_fields=["follower_count"])
            return Response({"followed": False, "follower_count": employer.follower_count})


# ── Similar Companies ─────────────────────────────────────────────────────────

class SimilarCompaniesView(APIView):
    """GET /company-intelligence/<slug>/similar/ — companies in same industry/size."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            employer = EmployerAccount.objects.get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response(status=404)

        similar = EmployerAccount.objects.filter(
            industry=employer.industry,
            is_verified=True,
        ).exclude(pk=employer.pk).order_by("-avg_rating", "-review_count")[:6]

        return Response([{
            "slug": c.slug,
            "name": c.company_name,
            "logo": c.logo.url if c.logo else None,
            "industry": str(c.industry) if c.industry else None,
            "size": c.company_size,
            "avg_rating": float(c.avg_rating),
            "review_count": c.review_count,
        } for c in similar])
