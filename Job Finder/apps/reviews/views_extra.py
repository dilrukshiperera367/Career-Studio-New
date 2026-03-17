"""
Feature 12 — Reviews, Q&A, and Community Proof
Extra views: interview reviews, benefits reviews, salary reviews, Q&A,
review summarization, authenticity signals, moderation transparency,
reviewer verification levels, employer response analytics, employer badges,
trending signals, tags, review-based company scoring.
"""
from django.db.models import Count, Avg, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView

from .models import (
    CompanyReview, ReviewHelpful, EmployerReviewResponse,
    InterviewReview, BenefitsReview, SalaryReview,
)


def _employer_from_slug(slug):
    from apps.employers.models import EmployerAccount
    return EmployerAccount.objects.filter(slug=slug).first()


# ── Interview Reviews ─────────────────────────────────────────────────────────

class InterviewReviewListCreateView(APIView):
    """GET/POST /reviews/interview/<slug>/"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)

        qs = InterviewReview.objects.filter(employer=employer, status="approved")
        stats = qs.aggregate(
            total=Count("id"),
            avg_difficulty=Avg("difficulty"),
            offer_rate=Count("id", filter=Q(got_offer=True)),
            positive=Count("id", filter=Q(experience="positive")),
            neutral=Count("id", filter=Q(experience="neutral")),
            negative=Count("id", filter=Q(experience="negative")),
        )

        reviews = qs.order_by("-created_at")[:20]
        return Response({
            "stats": {
                "total": stats["total"] or 0,
                "avg_difficulty": round(stats["avg_difficulty"] or 0, 1),
                "offer_rate_pct": round((stats["offer_rate"] or 0) / max(stats["total"] or 1, 1) * 100, 1),
                "experience_breakdown": {
                    "positive": stats["positive"] or 0,
                    "neutral": stats["neutral"] or 0,
                    "negative": stats["negative"] or 0,
                },
            },
            "reviews": [{
                "id": str(r.id),
                "job_title": r.job_title,
                "experience": r.experience,
                "difficulty": r.difficulty,
                "interview_type": r.interview_type,
                "num_rounds": r.num_rounds,
                "duration_days": r.duration_days,
                "got_offer": r.got_offer,
                "description": r.description,
                "questions_asked": r.questions_asked,
                "is_anonymous": r.is_anonymous,
                "created_at": r.created_at,
            } for r in reviews],
        })

    def post(self, request, slug):
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)

        d = request.data
        review = InterviewReview.objects.create(
            employer=employer,
            reviewer=request.user,
            job_title=d.get("job_title", ""),
            is_anonymous=bool(d.get("is_anonymous", True)),
            experience=d.get("experience", "neutral"),
            difficulty=int(d.get("difficulty", 3)),
            interview_type=d.get("interview_type", ""),
            num_rounds=d.get("num_rounds"),
            duration_days=d.get("duration_days"),
            got_offer=d.get("got_offer"),
            description=d.get("description", ""),
            questions_asked=d.get("questions_asked", []),
        )
        return Response({"id": str(review.id), "status": review.status,
                        "message": "Interview review submitted for moderation."}, status=201)


# ── Benefits Reviews ───────────────────────────────────────────────────────────

class BenefitsReviewListCreateView(APIView):
    """GET/POST /reviews/benefits/<slug>/"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)

        qs = BenefitsReview.objects.filter(employer=employer, status="approved")
        agg = qs.aggregate(
            total=Count("id"),
            avg_rating=Avg("overall_benefits_rating"),
            health_pct=Count("id", filter=Q(health_insurance=True)),
            remote_pct=Count("id", filter=Q(remote_work_option=True)),
            bonus_pct=Count("id", filter=Q(performance_bonus=True)),
        )
        total = agg["total"] or 1

        return Response({
            "stats": {
                "total": agg["total"] or 0,
                "avg_rating": round(agg["avg_rating"] or 0, 1),
                "health_insurance_pct": round((agg["health_pct"] or 0) / total * 100),
                "remote_work_pct": round((agg["remote_pct"] or 0) / total * 100),
                "performance_bonus_pct": round((agg["bonus_pct"] or 0) / total * 100),
            },
            "reviews": list(qs.order_by("-created_at")[:10].values(
                "id", "overall_benefits_rating", "health_insurance", "annual_leave_days",
                "remote_work_option", "performance_bonus", "pros", "cons", "created_at",
            )),
        })

    def post(self, request, slug):
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)
        d = request.data
        review = BenefitsReview.objects.create(
            employer=employer,
            reviewer=request.user,
            is_anonymous=bool(d.get("is_anonymous", True)),
            overall_benefits_rating=int(d.get("overall_benefits_rating", 3)),
            health_insurance=d.get("health_insurance"),
            annual_leave_days=d.get("annual_leave_days"),
            remote_work_option=d.get("remote_work_option"),
            performance_bonus=d.get("performance_bonus"),
            training_allowance=d.get("training_allowance"),
            transport_allowance=d.get("transport_allowance"),
            meal_allowance=d.get("meal_allowance"),
            pros=d.get("pros", ""),
            cons=d.get("cons", ""),
        )
        return Response({"id": str(review.id), "status": review.status}, status=201)


# ── Salary Reviews ────────────────────────────────────────────────────────────

class SalaryReviewListCreateView(APIView):
    """GET/POST /reviews/salary/<slug>/"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)

        qs = SalaryReview.objects.filter(employer=employer, status="approved")
        agg = qs.aggregate(
            total=Count("id"),
            avg_salary=Avg("base_salary_lkr"),
            avg_total_comp=Avg("total_comp_lkr"),
            avg_satisfaction=Avg("satisfaction_rating"),
        )

        # Breakdown by title
        by_title = list(
            qs.values("job_title")
            .annotate(count=Count("id"), avg_salary=Avg("base_salary_lkr"))
            .order_by("-count")[:10]
        )

        return Response({
            "stats": {
                "total": agg["total"] or 0,
                "avg_base_salary_lkr": round(agg["avg_salary"] or 0),
                "avg_total_comp_lkr": round(agg["avg_total_comp"] or 0),
                "avg_satisfaction": round(agg["avg_satisfaction"] or 0, 1),
            },
            "by_title": by_title,
            "recent": list(qs.order_by("-created_at")[:10].values(
                "id", "job_title", "base_salary_lkr", "total_comp_lkr", "satisfaction_rating",
                "experience_years", "is_verified", "created_at",
            )),
        })

    def post(self, request, slug):
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)
        d = request.data
        review = SalaryReview.objects.create(
            employer=employer,
            reviewer=request.user,
            is_anonymous=bool(d.get("is_anonymous", True)),
            job_title=d.get("job_title", ""),
            experience_years=d.get("experience_years"),
            base_salary_lkr=int(d.get("base_salary_lkr", 0)),
            total_comp_lkr=d.get("total_comp_lkr"),
            satisfaction_rating=int(d.get("satisfaction_rating", 3)),
            notes=d.get("notes", ""),
        )
        return Response({"id": str(review.id), "status": review.status}, status=201)


# ── Full Company Review Hub ───────────────────────────────────────────────────

class CompanyReviewHubView(APIView):
    """
    GET /reviews/hub/<slug>/
    Aggregated review intelligence: all review types + summary + badges.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)

        # Overall
        overall = CompanyReview.objects.filter(employer=employer, status="approved").aggregate(
            count=Count("id"),
            avg=Avg("overall_rating"),
            wlb=Avg("work_life_balance"),
            growth=Avg("career_growth"),
            comp=Avg("compensation"),
            mgmt=Avg("management"),
            culture=Avg("culture"),
        )

        # Interview
        int_stats = InterviewReview.objects.filter(employer=employer, status="approved").aggregate(
            count=Count("id"), avg_diff=Avg("difficulty"),
            offers=Count("id", filter=Q(got_offer=True))
        )

        # Benefits
        ben_stats = BenefitsReview.objects.filter(employer=employer, status="approved").aggregate(
            count=Count("id"), avg_rating=Avg("overall_benefits_rating")
        )

        # Salary
        sal_stats = SalaryReview.objects.filter(employer=employer, status="approved").aggregate(
            count=Count("id"), avg_sal=Avg("base_salary_lkr"), avg_sat=Avg("satisfaction_rating")
        )

        # Employer response analytics
        total_reviews = overall["count"] or 0
        responded = EmployerReviewResponse.objects.filter(
            review__employer=employer
        ).count()
        response_rate = round(responded / total_reviews * 100, 1) if total_reviews else 0

        # Review-based badges
        badges = []
        avg_rating = overall["avg"] or 0
        if avg_rating >= 4.5 and total_reviews >= 10:
            badges.append({"type": "top_rated", "label": "Top Rated Employer", "icon": "⭐"})
        if response_rate >= 70:
            badges.append({"type": "responsive", "label": "Highly Responsive", "icon": "💬"})
        if (ben_stats["avg_rating"] or 0) >= 4.0 and (ben_stats["count"] or 0) >= 5:
            badges.append({"type": "great_benefits", "label": "Great Benefits", "icon": "🎁"})
        if (overall["wlb"] or 0) >= 4.0 and total_reviews >= 5:
            badges.append({"type": "work_life_balance", "label": "Work-Life Balance", "icon": "⚡"})
        if (overall["growth"] or 0) >= 4.0 and total_reviews >= 5:
            badges.append({"type": "career_growth", "label": "Career Growth", "icon": "📈"})

        # Review summary (rule-based)
        summary = _generate_review_summary(overall, int_stats, ben_stats, sal_stats)

        # "Recently reviewed" signal
        from datetime import timedelta
        recent_reviews = CompanyReview.objects.filter(
            employer=employer, status="approved",
            created_at__gte=timezone.now() - timedelta(days=90)
        ).count()
        recently_reviewed = recent_reviews >= 2

        return Response({
            "employer_slug": slug,
            "employer_name": employer.company_name,
            "overall": {
                "total_reviews": total_reviews,
                "avg_rating": round(avg_rating, 1),
                "subtotals": {
                    "work_life_balance": round(overall["wlb"] or 0, 1),
                    "career_growth": round(overall["growth"] or 0, 1),
                    "compensation": round(overall["comp"] or 0, 1),
                    "management": round(overall["mgmt"] or 0, 1),
                    "culture": round(overall["culture"] or 0, 1),
                },
            },
            "interview": {
                "total": int_stats["count"] or 0,
                "avg_difficulty": round(int_stats["avg_diff"] or 0, 1),
                "offer_rate_pct": round((int_stats["offers"] or 0) / max(int_stats["count"] or 1, 1) * 100),
            },
            "benefits": {
                "total": ben_stats["count"] or 0,
                "avg_rating": round(ben_stats["avg_rating"] or 0, 1),
            },
            "salary": {
                "total": sal_stats["count"] or 0,
                "avg_base": round(sal_stats["avg_sal"] or 0),
                "avg_satisfaction": round(sal_stats["avg_sat"] or 0, 1),
            },
            "employer_response_analytics": {
                "total_reviews": total_reviews,
                "responded": responded,
                "response_rate_pct": response_rate,
            },
            "badges": badges,
            "summary": summary,
            "recently_reviewed": recently_reviewed,
            "recent_review_count_90d": recent_reviews,
        })


def _generate_review_summary(overall, int_stats, ben_stats, sal_stats):
    """Rule-based review summary string."""
    parts = []
    avg = overall.get("avg") or 0
    total = overall.get("count") or 0

    if total == 0:
        return "No reviews available yet for this employer."

    if avg >= 4.0:
        parts.append(f"Highly rated with {round(avg, 1)}/5.0 overall satisfaction across {total} reviews.")
    elif avg >= 3.0:
        parts.append(f"Mixed reviews — average {round(avg, 1)}/5.0 from {total} reviewers.")
    else:
        parts.append(f"Rated {round(avg, 1)}/5.0 — below average based on {total} reviews.")

    wlb = overall.get("wlb") or 0
    if wlb >= 4.0:
        parts.append("Employees rate work-life balance highly.")
    elif wlb and wlb < 3.0:
        parts.append("Work-life balance is a common concern in reviews.")

    offer_rate = round((int_stats.get("offers") or 0) / max((int_stats.get("count") or 1), 1) * 100)
    if (int_stats.get("count") or 0) >= 5:
        parts.append(f"{offer_rate}% of interviewees received an offer.")

    avg_sal = sal_stats.get("avg_sal") or 0
    if avg_sal > 0:
        parts.append(f"Reported median salary: LKR {int(avg_sal):,}/month.")

    return " ".join(parts)


# ── Company Q&A ───────────────────────────────────────────────────────────────

class CompanyQnAReviewView(APIView):
    """
    GET/POST /reviews/qna/<slug>/
    Community Q&A separate from company_intelligence (review-category Q&A).
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        from apps.company_intelligence.models import CompanyQnA
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)

        qnas = CompanyQnA.objects.filter(
            employer=employer, is_moderated=True
        ).order_by("-helpful_count", "-created_at")[:20]

        return Response([{
            "id": str(q.id),
            "question": q.question,
            "answer": q.answer,
            "helpful_count": q.helpful_count,
            "asked_by_type": "community",
            "created_at": q.created_at,
        } for q in qnas])

    def post(self, request, slug):
        from apps.company_intelligence.models import CompanyQnA
        employer = _employer_from_slug(slug)
        if not employer:
            return Response(status=404)
        qna = CompanyQnA.objects.create(
            employer=employer,
            asked_by=request.user,
            question=request.data.get("question", ""),
        )
        return Response({"id": str(qna.id), "message": "Question submitted for review."}, status=201)


# ── Moderation Transparency ───────────────────────────────────────────────────

class ModerationTransparencyView(APIView):
    """
    GET /reviews/moderation-stats/
    Public moderation stats to show review authenticity controls.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total = CompanyReview.objects.count()
        approved = CompanyReview.objects.filter(status="approved").count()
        rejected = CompanyReview.objects.filter(status="rejected").count()
        flagged = CompanyReview.objects.filter(status="flagged").count()

        return Response({
            "total_submitted": total,
            "approved": approved,
            "rejected": rejected,
            "flagged": flagged,
            "approval_rate_pct": round(approved / max(total, 1) * 100, 1),
            "moderation_policy": {
                "anonymous_allowed": True,
                "identity_verified": "Reviews from connected profiles are marked as verified",
                "employer_responses_allowed": True,
                "report_system": "Community can flag reviews; moderators review within 48h",
                "retention": "Reviews are kept for 24 months minimum",
                "removal_policy": "Only removed for verified policy violations or legal requirements",
            },
        })


# ── Reviewer Verification Level ───────────────────────────────────────────────

class ReviewerVerificationLevelView(APIView):
    """
    GET /reviews/reviewer-level/<uuid:review_id>/
    Authenticity signals for a review — verification level, helpful score.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, review_id):
        try:
            review = CompanyReview.objects.select_related("reviewer").get(pk=review_id)
        except CompanyReview.DoesNotExist:
            return Response(status=404)

        reviewer = review.reviewer
        signals = []
        verification_level = "anonymous"

        if reviewer:
            # Has applied to company's jobs
            from apps.applications.models import Application
            has_applied = Application.objects.filter(
                applicant=reviewer,
                job__employer=review.employer
            ).exists()
            if has_applied:
                signals.append("Applied for a job at this company")
                verification_level = "verified_applicant"

            # Has complete profile
            has_profile = hasattr(reviewer, "profile") and bool(reviewer.profile)
            if has_profile:
                signals.append("Complete JobFinder profile")

            # Account age
            from datetime import timedelta
            if (timezone.now() - reviewer.date_joined).days >= 30:
                signals.append("Account older than 30 days")

        helpful_votes = review.helpful_count

        return Response({
            "review_id": str(review.id),
            "verification_level": verification_level,
            "authenticity_signals": signals,
            "helpful_votes": helpful_votes,
            "is_anonymous": review.is_anonymous,
            "content_length": len(review.pros or "") + len(review.cons or ""),
            "authenticity_score": min(100, len(signals) * 25 + min(helpful_votes * 5, 25)),
        })


# ── Employer Response Analytics ───────────────────────────────────────────────

class EmployerResponseAnalyticsView(APIView):
    """
    GET /reviews/employer-response-analytics/
    Analytics for how/when the employer responds to reviews.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.employers.models import EmployerAccount
        employer = EmployerAccount.objects.filter(team_members__user=request.user).first()
        if not employer:
            return Response(status=403)

        total_reviews = CompanyReview.objects.filter(employer=employer, status="approved").count()
        responded = EmployerReviewResponse.objects.filter(review__employer=employer)
        responded_count = responded.count()

        # Avg response time in days
        avg_response_hours = None
        for resp in responded[:20]:
            delta = resp.created_at - resp.review.created_at
            if avg_response_hours is None:
                avg_response_hours = delta.total_seconds() / 3600
            else:
                avg_response_hours = (avg_response_hours + delta.total_seconds() / 3600) / 2

        # Reviews without response
        unresponded = CompanyReview.objects.filter(
            employer=employer, status="approved", employer_response__isnull=True
        ).order_by("-created_at")[:5]

        return Response({
            "total_approved_reviews": total_reviews,
            "responded": responded_count,
            "response_rate_pct": round(responded_count / max(total_reviews, 1) * 100, 1),
            "avg_response_hours": round(avg_response_hours, 1) if avg_response_hours else None,
            "unresponded_reviews": [{
                "id": str(r.id),
                "overall_rating": r.overall_rating,
                "title": r.title,
                "created_at": r.created_at,
            } for r in unresponded],
            "tips": [
                "Responding to reviews increases candidate trust by ~30%",
                "Respond to negative reviews within 48 hours for best results",
                "Thank reviewers even for critical feedback",
            ],
        })
