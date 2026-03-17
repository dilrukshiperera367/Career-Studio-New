"""Analytics utility services — trend reports, rejection analytics, advanced reporting."""

import logging
from django.utils import timezone
from django.db.models import Count, Avg, Q, F

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trend Reports — Month-over-Month (Feature 93)
# ---------------------------------------------------------------------------

def generate_trend_report(tenant_id: str, months: int = 6) -> dict:
    """Generate month-over-month comparison metrics."""
    from apps.applications.models import Application, Interview, Offer
    import datetime

    trends = []
    now = timezone.now()

    for i in range(months):
        month_start = (now.replace(day=1) - datetime.timedelta(days=i * 30)).replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        apps = Application.objects.filter(
            tenant_id=tenant_id,
            created_at__gte=month_start,
            created_at__lt=month_end,
        )
        hires = apps.filter(status="hired")
        interviews = Interview.objects.filter(
            tenant_id=tenant_id,
            created_at__gte=month_start,
            created_at__lt=month_end,
        )
        offers = Offer.objects.filter(
            tenant_id=tenant_id,
            created_at__gte=month_start,
            created_at__lt=month_end,
        )

        # Average time-to-hire for hires in this month
        hired_apps = apps.filter(status="hired", updated_at__isnull=False)
        avg_tth = None
        if hired_apps.exists():
            tth_values = [
                (a.updated_at - a.created_at).days for a in hired_apps
                if a.updated_at and a.created_at
            ]
            avg_tth = round(sum(tth_values) / len(tth_values), 1) if tth_values else None

        trends.append({
            "month": month_start.strftime("%Y-%m"),
            "applications": apps.count(),
            "hires": hires.count(),
            "interviews": interviews.count(),
            "offers_made": offers.count(),
            "offers_accepted": offers.filter(status="accepted").count(),
            "avg_time_to_hire_days": avg_tth,
        })

    # Calculate month-over-month changes
    for i in range(len(trends) - 1):
        current = trends[i]
        previous = trends[i + 1]
        for key in ["applications", "hires", "interviews"]:
            prev_val = previous.get(key, 0)
            curr_val = current.get(key, 0)
            if prev_val > 0:
                change = round((curr_val - prev_val) / prev_val * 100, 1)
                current[f"{key}_change_pct"] = change
            else:
                current[f"{key}_change_pct"] = None

    return {"months": months, "trends": list(reversed(trends))}


# ---------------------------------------------------------------------------
# Rejection Analytics (Feature 164)
# ---------------------------------------------------------------------------

def rejection_analytics(tenant_id: str, job_id: str = None) -> dict:
    """Most common rejection reasons by stage, by job, by department."""
    from apps.applications.models import Application
    from apps.jobs.models import Job

    filters = {"tenant_id": tenant_id, "status": "rejected"}
    if job_id:
        filters["job_id"] = job_id

    rejected = Application.objects.filter(**filters)

    # By reason
    by_reason = list(
        rejected.exclude(rejection_reason="").values("rejection_reason").annotate(
            count=Count("id")
        ).order_by("-count")[:10]
    )

    # By stage
    by_stage = list(
        rejected.values("current_stage").annotate(
            count=Count("id")
        ).order_by("-count")[:10]
    )

    # By department (through job)
    by_department = list(
        rejected.values("job__department").annotate(
            count=Count("id")
        ).order_by("-count")[:10]
    )

    return {
        "total_rejected": rejected.count(),
        "by_reason": by_reason,
        "by_stage": by_stage,
        "by_department": by_department,
    }


# ---------------------------------------------------------------------------
# Interview-to-Hire Ratio (Feature 170)
# ---------------------------------------------------------------------------

def interview_to_hire_ratio(tenant_id: str, job_id: str = None) -> dict:
    """How many interviews needed per hire? By job, interviewer, department."""
    from apps.applications.models import Application, Interview
    from apps.jobs.models import Job

    job_filter = {"tenant_id": tenant_id}
    if job_id:
        job_filter["job_id"] = job_id

    total_interviews = Interview.objects.filter(**job_filter).count()
    total_hires = Application.objects.filter(**job_filter, status="hired").count()

    overall_ratio = round(total_interviews / total_hires, 1) if total_hires > 0 else None

    # By job
    by_job = []
    jobs = Job.objects.filter(tenant_id=tenant_id)
    if job_id:
        jobs = jobs.filter(id=job_id)

    for job in jobs[:20]:
        j_interviews = Interview.objects.filter(tenant_id=tenant_id, job=job).count()
        j_hires = Application.objects.filter(tenant_id=tenant_id, job=job, status="hired").count()
        if j_hires > 0:
            by_job.append({
                "job_id": str(job.id),
                "title": job.title,
                "interviews": j_interviews,
                "hires": j_hires,
                "ratio": round(j_interviews / j_hires, 1),
            })

    # By interviewer
    by_interviewer = list(
        Interview.objects.filter(**job_filter).values(
            "interviewer__first_name", "interviewer__last_name", "interviewer_id"
        ).annotate(
            interview_count=Count("id")
        ).order_by("-interview_count")[:10]
    )

    return {
        "total_interviews": total_interviews,
        "total_hires": total_hires,
        "overall_ratio": overall_ratio,
        "by_job": by_job,
        "by_interviewer": by_interviewer,
    }


# ---------------------------------------------------------------------------
# Offer Comparison Tool (Feature 151)
# ---------------------------------------------------------------------------

def offer_comparison(tenant_id: str, job_id: str) -> dict:
    """Compare current offers with previous offers for the same role."""
    from apps.applications.models import Offer
    from apps.jobs.models import Job

    try:
        job = Job.objects.get(id=job_id, tenant_id=tenant_id)
    except Job.DoesNotExist:
        return {"error": "Job not found"}

    # Get all offers for same title/department
    similar_offers = Offer.objects.filter(
        tenant_id=tenant_id,
        application__job__title__iexact=job.title,
    ).exclude(salary_offered__isnull=True)

    current_offers = similar_offers.filter(application__job_id=job_id)
    historical_offers = similar_offers.exclude(application__job_id=job_id)

    def _offer_stats(qs):
        if not qs.exists():
            return None
        return {
            "count": qs.count(),
            "avg_salary": float(qs.aggregate(avg=Avg("salary_offered"))["avg"] or 0),
            "accepted": qs.filter(status="accepted").count(),
            "declined": qs.filter(status="declined").count(),
            "acceptance_rate": round(
                qs.filter(status="accepted").count() / max(qs.count(), 1) * 100, 1
            ),
        }

    return {
        "job_id": str(job_id),
        "job_title": job.title,
        "current_offers": _offer_stats(current_offers),
        "historical_offers": _offer_stats(historical_offers),
        "salary_range": {
            "min": float(job.salary_min) if job.salary_min else None,
            "max": float(job.salary_max) if job.salary_max else None,
        },
    }


# ---------------------------------------------------------------------------
# Hiring Committee Voting Tally (Feature 103)
# ---------------------------------------------------------------------------

def voting_tally(tenant_id: str, application_id: str) -> dict:
    """Aggregate interview panel votes for an application."""
    from apps.applications.models import Interview, InterviewPanel

    panels = InterviewPanel.objects.filter(
        interview__tenant_id=tenant_id,
        interview__application_id=application_id,
        status="submitted",
    )

    votes = {
        "total_voters": panels.count(),
        "avg_rating": None,
        "votes": [],
        "consensus": None,
    }

    if not panels.exists():
        return votes

    ratings = [p.rating for p in panels if p.rating is not None]
    if ratings:
        votes["avg_rating"] = round(sum(ratings) / len(ratings), 1)

    for p in panels:
        recommendation = "yes" if (p.rating or 0) >= 4 else ("maybe" if (p.rating or 0) >= 3 else "no")
        votes["votes"].append({
            "interviewer_id": str(p.interviewer_id),
            "interviewer_name": f"{p.interviewer.first_name} {p.interviewer.last_name}",
            "rating": p.rating,
            "recommendation": recommendation,
            "feedback": p.feedback,
        })

    # Determine consensus
    recommendations = [v["recommendation"] for v in votes["votes"]]
    yes_count = recommendations.count("yes")
    no_count = recommendations.count("no")
    total = len(recommendations)

    if yes_count / total >= 0.75:
        votes["consensus"] = "strong_yes"
    elif yes_count / total >= 0.5:
        votes["consensus"] = "yes"
    elif no_count / total >= 0.75:
        votes["consensus"] = "strong_no"
    elif no_count / total >= 0.5:
        votes["consensus"] = "no"
    else:
        votes["consensus"] = "split"

    return votes


# ---------------------------------------------------------------------------
# Score Comparison Across Jobs (Feature 46)
# ---------------------------------------------------------------------------

def score_comparison_across_jobs(tenant_id: str, candidate_id: str) -> list:
    """Show which job a candidate scores highest for."""
    from apps.applications.models import Application

    applications = Application.objects.filter(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    ).select_related("job")

    results = []
    for app in applications:
        results.append({
            "application_id": str(app.id),
            "job_id": str(app.job_id),
            "job_title": app.job.title if app.job else "",
            "score": float(app.score or 0),
            "status": app.status,
            "current_stage": app.current_stage,
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    if results:
        results[0]["recommended"] = True

    return results


# ---------------------------------------------------------------------------
# Batch Re-Scoring (Feature 44)
# ---------------------------------------------------------------------------

def batch_rescore(tenant_id: str, job_id: str) -> dict:
    """Re-score all candidates for a job against updated requirements."""
    from apps.applications.models import Application
    from apps.search.ranking import rank_candidates

    applications = Application.objects.filter(
        tenant_id=tenant_id,
        job_id=job_id,
        status="active",
    )

    rescored = 0
    errors = 0
    for app in applications[:500]:
        try:
            scores = rank_candidates(
                tenant_id=tenant_id,
                job_id=job_id,
                candidate_ids=[str(app.candidate_id)],
            )
            if scores:
                new_score = scores[0].get("final_score", app.score)
                if new_score != app.score:
                    app.score = new_score
                    app.save(update_fields=["score", "updated_at"])
                    rescored += 1
        except Exception as e:
            logger.error(f"Rescore failed for app {app.id}: {e}")
            errors += 1

    return {
        "job_id": str(job_id),
        "total_candidates": applications.count(),
        "rescored": rescored,
        "errors": errors,
    }
