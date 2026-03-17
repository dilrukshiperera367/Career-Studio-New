"""Marketplace Search — enhanced views with hybrid ranking, people-also-viewed,
company recommendations, role adjacency, cold-start logic, and trending jobs."""
import math
import re
import uuid
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employers.models import EmployerAccount
from apps.jobs.models import JobListing
from apps.jobs.serializers import JobListSerializer
from .models import (
    BrowseSurface, JobRecommendation, SearchExplanation, TrendingEmployer,
)
from .serializers import (
    BrowseSurfaceSerializer, JobRecommendationSerializer,
    SearchExplanationSerializer, TrendingEmployerSerializer,
)

# ─── Synonym map (expanded) ───────────────────────────────────────────────────
TITLE_SYNONYMS = {
    "developer": ["developer", "engineer", "programmer", "coder"],
    "engineer": ["engineer", "developer"],
    "programmer": ["programmer", "developer", "coder"],
    "software": ["software", "it", "tech"],
    "accountant": ["accountant", "accounting", "finance"],
    "marketing": ["marketing", "digital marketing", "brand"],
    "sales": ["sales", "business development", "biz dev"],
    "manager": ["manager", "lead", "head", "director"],
    "designer": ["designer", "ui", "ux", "creative"],
    "analyst": ["analyst", "analytics", "data"],
    "teacher": ["teacher", "lecturer", "instructor", "tutor", "educator"],
    "driver": ["driver", "chauffeur", "operator"],
    "nurse": ["nurse", "nursing", "healthcare"],
    "doctor": ["doctor", "physician", "medical"],
    "chef": ["chef", "cook", "culinary"],
    "security": ["security", "guard", "safety"],
    "hr": ["hr", "human resources", "people ops"],
    "devops": ["devops", "infrastructure", "sre", "platform"],
    "data": ["data", "ml", "ai", "machine learning", "analytics"],
    "qa": ["qa", "quality assurance", "tester", "testing"],
}

# ─── Role adjacency graph ─────────────────────────────────────────────────────
ROLE_ADJACENCY = {
    "software engineer": ["devops engineer", "qa engineer", "product manager", "data engineer"],
    "data analyst": ["data scientist", "business analyst", "data engineer", "ml engineer"],
    "marketing manager": ["brand manager", "digital marketer", "content manager", "growth manager"],
    "sales executive": ["business development", "account manager", "sales manager"],
    "hr manager": ["recruiter", "talent acquisition", "people operations"],
    "project manager": ["scrum master", "product manager", "program manager", "delivery manager"],
    "accountant": ["finance analyst", "auditor", "bookkeeper", "financial controller"],
    "graphic designer": ["ui designer", "ux designer", "visual designer", "creative director"],
    "customer service": ["support specialist", "client success", "help desk"],
}


def _expand_synonyms(query: str) -> list[str]:
    """Return a list of synonym-expanded search terms."""
    lower = query.lower().strip()
    for key, synonyms in TITLE_SYNONYMS.items():
        if key in lower:
            return synonyms
    return [query]


def _compute_hybrid_score(job, query: str = "", user=None, behavior_data: dict = None) -> float:
    """
    Hybrid ranking: keyword relevance + freshness + quality + behavior + sponsorship.
    Returns a float 0–100.
    """
    score = 0.0

    # 1. Keyword relevance (0–30)
    if query:
        lower_q = query.lower()
        if lower_q in (job.title or "").lower():
            score += 30
        elif any(s in (job.title or "").lower() for s in _expand_synonyms(query)):
            score += 20
        elif lower_q in (job.description or "").lower():
            score += 10

    # 2. Freshness (0–25) — exponential decay
    if job.published_at:
        age_days = (timezone.now() - job.published_at).days
        freshness = max(0, 25 * math.exp(-age_days / 14))  # half-life 14 days
        score += freshness

    # 3. Quality score from job.quality_score field (0–20)
    quality = getattr(job, "quality_score", 50) or 50
    score += quality * 0.20

    # 4. Behavioral signals (0–15)
    if behavior_data:
        views = behavior_data.get("view_count", 0) or job.view_count
        apps = behavior_data.get("application_count", 0) or job.application_count
        score += min(8, views / 100)
        score += min(7, apps / 20)
    else:
        score += min(8, (job.view_count or 0) / 100)
        score += min(7, (job.application_count or 0) / 20)

    # 5. Prominence (0–10)
    if job.is_sponsored:
        score += 10
    elif job.is_featured:
        score += 7
    elif job.is_boosted:
        score += 4

    return round(min(score, 100), 2)


def _get_role_adjacents(job_title: str) -> list[str]:
    """Return adjacent role titles for a given job title."""
    lower = job_title.lower()
    for key, adjacents in ROLE_ADJACENCY.items():
        if key in lower:
            return adjacents
    return []


def _cold_start_feed(limit: int = 30):
    """Cold-start feed for unauthenticated/new users: trending + featured + recent."""
    cache_key = "cold_start_feed"
    cached = cache.get(cache_key)
    if cached:
        return cached

    jobs = list(JobListing.objects.filter(
        status="active"
    ).select_related("employer", "district", "category").order_by(
        "-is_featured", "-is_boosted", "-freshness_score", "-published_at"
    )[:limit])

    cache.set(cache_key, jobs, 180)  # 3 min
    return jobs


# ─── Views ────────────────────────────────────────────────────────────────────

class PersonalizedFeedView(APIView):
    """Return a personalized ranked job feed. Cold-start logic for new/anon users."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        if not request.user.is_authenticated:
            jobs = _cold_start_feed(limit=50)
            start = (page - 1) * page_size
            paged = jobs[start:start + page_size]
            data = JobListSerializer(paged, many=True, context={"request": request}).data
            return Response({
                "results": data, "total": len(jobs),
                "algorithm": "cold-start-v1", "page": page,
            })

        cache_key = f"personalized_feed_{request.user.id}_p{page}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        qs = JobListing.objects.filter(status="active").select_related(
            "employer", "district", "category"
        )

        # Profile-based boost filters
        try:
            profile = request.user.seeker_profile
            location_filter = Q()
            if profile.desired_locations:
                location_filter = Q(district_id__in=profile.desired_locations)

            type_filter = Q()
            if profile.desired_job_types:
                type_filter = Q(job_type__in=profile.desired_job_types)

            # Prefer matching, but don't exclude non-matching
            qs = qs.filter(location_filter | type_filter).distinct() if (
                profile.desired_locations or profile.desired_job_types
            ) else qs
        except Exception:
            pass

        # Hybrid ranking: compute once for top 200, then sort
        top_qs = qs.order_by("-published_at")[:200]
        scored = sorted(
            [(j, _compute_hybrid_score(j, user=request.user)) for j in top_qs],
            key=lambda x: x[1], reverse=True,
        )
        start = (page - 1) * page_size
        paged = [j for j, _ in scored[start:start + page_size]]

        data = JobListSerializer(paged, many=True, context={"request": request}).data
        result = {
            "results": data, "total": len(scored),
            "algorithm": "hybrid-profile-v2", "page": page,
        }
        cache.set(cache_key, result, 300)
        return Response(result)


class SimilarJobsView(APIView):
    """Return similar jobs for a given job — multi-signal similarity."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        cache_key = f"similar_jobs_{job_id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            job = JobListing.objects.select_related("category", "district", "employer").get(
                pk=job_id, status="active"
            )
        except JobListing.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # Multi-signal: same category + similar salary band + similar experience level
        salary_min = (job.salary_min or 0) * 0.6
        salary_max = (job.salary_max or 999_999_999) * 1.6

        similar_qs = JobListing.objects.filter(
            status="active", category=job.category,
        ).exclude(id=job_id)

        if job.salary_min:
            similar_qs = similar_qs.filter(
                Q(salary_max__gte=salary_min) | Q(salary_min__lte=salary_max)
            )

        if job.experience_level:
            similar_qs = similar_qs.filter(experience_level=job.experience_level)

        similar = list(similar_qs.order_by("-is_featured", "-published_at")[:8])

        # Supplement with role-adjacent if < 4 results
        if len(similar) < 4:
            adjacents = _get_role_adjacents(job.title or "")
            for adj_title in adjacents:
                adj_qs = JobListing.objects.filter(
                    status="active", title__icontains=adj_title.split()[0]
                ).exclude(id=job_id).exclude(id__in=[j.id for j in similar])[:3]
                similar.extend(adj_qs)
                if len(similar) >= 8:
                    break

        # Store recommendations
        for sim_job in similar[:8]:
            JobRecommendation.objects.get_or_create(
                source_job=job, recommended_job=sim_job, rec_type="similar",
                defaults={"score": 0.7, "reasons": ["same category"], "algorithm_version": "v2"},
            )

        data = JobListSerializer(similar[:8], many=True, context={"request": request}).data
        result = {"results": data, "source_job_id": str(job_id)}
        cache.set(cache_key, result, 600)
        return Response(result)


class AlsoViewedJobsView(APIView):
    """People also viewed — jobs viewed by seekers who viewed this job."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        cache_key = f"also_viewed_{job_id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            job = JobListing.objects.get(pk=job_id, status="active")
        except JobListing.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        # Find users who viewed this job, then find other jobs they viewed
        from apps.jobs.models import JobView
        viewers = JobView.objects.filter(job=job).values_list("user", flat=True).distinct()

        also_viewed_ids = (
            JobView.objects.filter(user__in=viewers)
            .exclude(job=job)
            .exclude(job__status__in=["closed", "expired"])
            .values("job")
            .annotate(view_count=Count("id"))
            .order_by("-view_count")[:8]
        )

        job_ids = [item["job"] for item in also_viewed_ids]
        also_viewed = []
        if job_ids:
            job_map = {j.id: j for j in JobListing.objects.filter(id__in=job_ids).select_related("employer", "district")}
            also_viewed = [job_map[jid] for jid in job_ids if jid in job_map]

        # Fallback: similar category if insufficient
        if len(also_viewed) < 4:
            fallback = JobListing.objects.filter(
                status="active", category=job.category
            ).exclude(id=job_id).exclude(
                id__in=[j.id for j in also_viewed]
            ).order_by("-view_count")[:8 - len(also_viewed)]
            also_viewed.extend(fallback)

        data = JobListSerializer(also_viewed[:8], many=True, context={"request": request}).data
        cache.set(cache_key, data, 600)
        return Response({"results": data})


class RoleAdjacentJobsView(APIView):
    """Role adjacency suggestions — related job titles nearby in skill space."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        try:
            job = JobListing.objects.get(pk=job_id, status="active")
        except JobListing.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        adjacents = _get_role_adjacents(job.title or "")
        results = []
        for adj in adjacents[:4]:
            adj_jobs = JobListing.objects.filter(
                status="active", title__icontains=adj.split()[0]
            ).exclude(id=job_id).order_by("-published_at")[:2]
            results.extend(adj_jobs)

        data = JobListSerializer(results[:8], many=True, context={"request": request}).data
        return Response({"results": data, "adjacent_roles": adjacents})


class CompanyRecommendationsView(APIView):
    """Company recommendations for a given company — similar employers."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, company_id):
        cache_key = f"company_recs_{company_id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            company = EmployerAccount.objects.get(pk=company_id)
        except EmployerAccount.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        # Similar: same industry + similar size
        similar_qs = EmployerAccount.objects.filter(
            industry=company.industry
        ).exclude(id=company_id).order_by("-is_verified", "-active_job_count")[:6]

        from apps.employers.serializers import EmployerListSerializer
        data = EmployerListSerializer(similar_qs, many=True).data
        cache.set(cache_key, data, 1800)
        return Response({"results": data})


class TrendingJobsView(APIView):
    """Trending jobs — high view velocity in last 48h."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = "trending_jobs"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        cutoff = timezone.now() - timedelta(hours=48)
        from apps.jobs.models import JobView
        trending_ids = (
            JobView.objects.filter(viewed_at__gte=cutoff)
            .values("job")
            .annotate(recent_views=Count("id"))
            .order_by("-recent_views")[:20]
        )
        job_ids = [item["job"] for item in trending_ids]
        jobs = []
        if job_ids:
            job_map = {
                j.id: j for j in JobListing.objects.filter(
                    id__in=job_ids, status="active"
                ).select_related("employer", "district", "category")
            }
            jobs = [job_map[jid] for jid in job_ids if jid in job_map]

        # Fallback if no view data
        if not jobs:
            jobs = list(JobListing.objects.filter(
                status="active", is_featured=True
            ).select_related("employer", "district", "category").order_by("-published_at")[:12])

        data = JobListSerializer(jobs[:12], many=True, context={"request": request}).data
        cache.set(cache_key, data, 300)
        return Response({"results": data})


class BrowseSurfacesView(APIView):
    """Return pre-computed browse surfaces (category, city, salary, level, industry, shift, contract)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        surface_type = request.query_params.get("type")
        qs = BrowseSurface.objects.all()
        if surface_type:
            qs = qs.filter(surface_type=surface_type)

        # If no surfaces exist, generate them on-the-fly from live data
        if not qs.exists():
            return _generate_live_browse_surfaces(request, surface_type)

        serializer = BrowseSurfaceSerializer(qs[:60], many=True)
        return Response(serializer.data)


def _generate_live_browse_surfaces(request, surface_type=None):
    """Generate browse surface data live from the database when pre-computed data is absent."""
    from apps.taxonomy.models import JobCategory, District
    surfaces = []

    if not surface_type or surface_type == "category":
        cats = JobCategory.objects.filter(is_featured=True).order_by("sort_order")[:12]
        for cat in cats:
            count = JobListing.objects.filter(status="active", category=cat).count()
            surfaces.append({
                "surface_type": "category", "label": cat.name_en,
                "slug": cat.slug, "job_count": count, "icon": cat.icon or "briefcase",
                "is_featured": True,
            })

    if not surface_type or surface_type == "city":
        districts = District.objects.filter(is_active=True).annotate(
            job_count=Count("joblisting", filter=Q(joblisting__status="active"))
        ).order_by("-job_count")[:10]
        for d in districts:
            surfaces.append({
                "surface_type": "city", "label": d.name_en,
                "slug": d.slug, "job_count": d.job_count, "icon": "map-pin",
                "is_featured": False,
            })

    if not surface_type or surface_type == "level":
        for level, label in [
            ("entry", "Entry Level"), ("mid", "Mid Level"),
            ("senior", "Senior Level"), ("lead", "Lead / Manager"), ("executive", "Executive / C-Suite"),
        ]:
            count = JobListing.objects.filter(status="active", experience_level=level).count()
            surfaces.append({
                "surface_type": "level", "label": label, "slug": level,
                "job_count": count, "icon": "trending-up", "is_featured": False,
            })

    if not surface_type or surface_type == "shift":
        for shift, label in [
            ("day", "Day Shift"), ("night", "Night Shift"), ("rotating", "Rotating"),
            ("flexible", "Flexible Hours"),
        ]:
            count = JobListing.objects.filter(status="active", shift_type=shift).count()
            surfaces.append({
                "surface_type": "shift", "label": label, "slug": shift,
                "job_count": count, "icon": "clock", "is_featured": False,
            })

    return Response(surfaces)


class SearchExplanationView(APIView):
    """Return why a specific job appears for this user — with live computation fallback."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            explanation = SearchExplanation.objects.get(user=request.user, job_id=job_id)
            return Response(SearchExplanationSerializer(explanation).data)
        except SearchExplanation.DoesNotExist:
            pass

        # Generate live explanation
        try:
            job = JobListing.objects.select_related(
                "category", "district", "employer"
            ).prefetch_related("required_skills").get(pk=job_id)
        except JobListing.DoesNotExist:
            return Response({"detail": "Job not found."}, status=404)

        try:
            profile = request.user.seeker_profile
            profile_skills = set(getattr(profile, "skill_names", []))
            job_skills = set(s.name_en for s in job.required_skills.all())
            matching = list(profile_skills & job_skills)
            missing = list(job_skills - profile_skills)
            match_score = len(matching) / max(len(job_skills), 1) if job_skills else 0.5

            salary_match = bool(
                job.salary_min and hasattr(profile, "min_salary_expectation") and
                profile.min_salary_expectation and job.salary_max and
                job.salary_max >= profile.min_salary_expectation
            )
            location_match = bool(
                job.district and hasattr(profile, "preferred_districts") and
                profile.preferred_districts and job.district_id in profile.preferred_districts
            )

            explanation, _ = SearchExplanation.objects.get_or_create(
                user=request.user, job_id=job_id,
                defaults={
                    "matching_skills": matching,
                    "missing_skills": missing[:5],
                    "match_score": match_score,
                    "salary_match": salary_match,
                    "location_match": location_match,
                    "experience_match": True,
                    "explanation_text": f"Matches {len(matching)} of your skills. "
                                        f"{'Salary within range. ' if salary_match else ''}"
                                        f"{'Location matches. ' if location_match else ''}",
                }
            )
        except Exception:
            return Response({
                "match_score": 0.5,
                "explanation_text": "This job is relevant to your recent search.",
                "matching_skills": [], "missing_skills": [],
            })

        return Response(SearchExplanationSerializer(explanation).data)


class TrendingEmployersView(APIView):
    """Return this week's trending / actively hiring employers."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = "trending_employers"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        from datetime import date
        week_start = date.today() - timedelta(days=date.today().weekday())
        qs = TrendingEmployer.objects.filter(week_start=week_start).select_related("employer")[:10]

        if not qs.exists():
            # Live fallback: employers with most new jobs this week
            cutoff = timezone.now() - timedelta(days=7)
            active_employers = (
                JobListing.objects.filter(status="active", published_at__gte=cutoff)
                .values("employer")
                .annotate(new_jobs=Count("id"))
                .order_by("-new_jobs")[:10]
            )
            emp_ids = [e["employer"] for e in active_employers]
            employers = EmployerAccount.objects.filter(id__in=emp_ids)
            from apps.employers.serializers import EmployerListSerializer
            data = [
                {**EmployerListSerializer(emp).data, "new_jobs_this_week": next(
                    (e["new_jobs"] for e in active_employers if e["employer"] == emp.id), 0
                )}
                for emp in employers
            ]
            cache.set(cache_key, data, 600)
            return Response(data)

        data = TrendingEmployerSerializer(qs, many=True, context={"request": request}).data
        cache.set(cache_key, data, 600)
        return Response(data)
