"""Search views — Full-text job search, company search, suggestions, trending, analytics.
Uses DB queries for now; OpenSearch integration in production.
Features #86–135.
"""
from django.core.cache import cache
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobListing
from apps.jobs.serializers import JobListSerializer
from apps.employers.models import EmployerAccount
from apps.employers.serializers import EmployerListSerializer
from apps.analytics.models import SearchLog
from apps.taxonomy.models import Skill
from .serializers import JobSearchSerializer, CompanySearchSerializer, SearchSuggestionSerializer


class JobSearchView(APIView):
    """Main job search endpoint with full filtering (#86–135)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = JobSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = JobListing.objects.filter(
            status="active",
        ).select_related("employer", "district", "category", "subcategory", "industry")

        # Text search with synonym expansion (#133)
        if q := data.get("q"):
            lang = data.get("lang", "en")
            search_q = self._expand_synonyms(q)
            if lang == "si":
                qs = qs.filter(Q(title_si__icontains=search_q) | Q(description_si__icontains=search_q))
            elif lang == "ta":
                qs = qs.filter(Q(title_ta__icontains=search_q) | Q(description_ta__icontains=search_q))
            else:
                # Mixed-language search (#57)
                qs = qs.filter(
                    Q(title__icontains=q) | Q(description__icontains=q) |
                    Q(title_si__icontains=q) | Q(title_ta__icontains=q) |
                    Q(required_skills__name_en__icontains=q) |
                    Q(employer__company_name__icontains=q)
                ).distinct()

        # Filters (#99–119)
        if cat := data.get("category"):
            qs = qs.filter(category_id=cat)
        if sub := data.get("subcategory"):
            qs = qs.filter(subcategory_id=sub)
        if dist := data.get("district"):
            qs = qs.filter(district_id=dist)
        if prov := data.get("province"):
            qs = qs.filter(district__province_id=prov)
        if ind := data.get("industry"):
            qs = qs.filter(industry_id=ind)
        if jt := data.get("job_type"):
            qs = qs.filter(job_type=jt)
        if el := data.get("experience_level"):
            qs = qs.filter(experience_level=el)
        if wa := data.get("work_arrangement"):
            qs = qs.filter(work_arrangement=wa)
        if ed := data.get("education_level"):
            qs = qs.filter(education_level=ed)
        if smin := data.get("salary_min"):
            qs = qs.filter(salary_max__gte=smin)
        if smax := data.get("salary_max"):
            qs = qs.filter(salary_min__lte=smax)
        if skills := data.get("skills"):
            qs = qs.filter(required_skills__id__in=skills).distinct()
        if employer_id := data.get("employer"):
            qs = qs.filter(employer_id=employer_id)
        if lang_req := data.get("language_required"):
            qs = qs.filter(language_requirements__contains=[{"lang": lang_req}])
        if company_size := data.get("company_size"):
            qs = qs.filter(employer__company_size=company_size)

        # Toggle filters (#115–119)
        if data.get("verified_only"):
            qs = qs.filter(employer__is_verified=True)
        if data.get("salary_shown"):
            qs = qs.filter(salary_min__isnull=False)
        if data.get("government_only"):
            qs = qs.filter(category__slug="government")
        if data.get("foreign_only"):
            qs = qs.filter(category__slug="foreign-employment")
        # Advanced filters (new)
        if data.get("visa_sponsorship"):
            qs = qs.filter(visa_sponsorship=True)
        if shift := data.get("shift_type"):
            qs = qs.filter(shift_type=shift)
        if ct := data.get("contract_type"):
            qs = qs.filter(job_type=ct)
        if data.get("quick_apply"):
            qs = qs.filter(quick_apply_enabled=True)
        if data.get("remote_only"):
            qs = qs.filter(work_arrangement="remote")

        # Posted within (#109)
        from datetime import timedelta
        pw = data.get("posted_within", "")
        if pw == "24h":
            qs = qs.filter(published_at__gte=timezone.now() - timedelta(hours=24))
        elif pw == "3d":
            qs = qs.filter(published_at__gte=timezone.now() - timedelta(days=3))
        elif pw == "7d":
            qs = qs.filter(published_at__gte=timezone.now() - timedelta(days=7))
        elif pw == "30d":
            qs = qs.filter(published_at__gte=timezone.now() - timedelta(days=30))

        # Sort (#120–125)
        sort = data.get("sort", "relevance")
        from apps.jobs.models import JobView
        if sort == "date":
            qs = qs.order_by("-published_at")
        elif sort == "salary_desc":
            qs = qs.order_by("-salary_max")
        elif sort == "salary_asc":
            qs = qs.order_by("salary_min")
        elif sort == "closing_date":
            qs = qs.filter(expires_at__isnull=False).order_by("expires_at")
        elif sort == "trending":
            # Trending: most views in last 48h
            cutoff = timezone.now() - timedelta(hours=48)
            trending_ids = list(
                JobView.objects.filter(viewed_at__gte=cutoff)
                .values("job")
                .annotate(recent_views=Count("id"))
                .order_by("-recent_views")
                .values_list("job", flat=True)[:200]
            )
            if trending_ids:
                from django.db.models import Case, When, IntegerField
                ordering = Case(
                    *[When(id=jid, then=pos) for pos, jid in enumerate(trending_ids)],
                    default=len(trending_ids),
                    output_field=IntegerField(),
                )
                qs = qs.filter(id__in=trending_ids).order_by(ordering)
            else:
                qs = qs.order_by("-is_featured", "-is_boosted", "-published_at")
        else:
            qs = qs.order_by("-is_featured", "-is_boosted", "-published_at")

        # Pagination
        page = data.get("page", 1)
        page_size = data.get("page_size", 20)
        total = qs.count()
        start = (page - 1) * page_size
        results = qs[start:start + page_size]

        # Log search (#135)
        SearchLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            query=data.get("q", ""),
            filters={k: str(v) for k, v in data.items() if v and k not in ("q", "page", "page_size")},
            results_count=total,
            language=data.get("lang", "en"),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # No results suggestions (#131)
        suggestions = []
        if total == 0 and data.get("q"):
            spell = self._spell_correct(data["q"])
            if spell != data["q"]:
                suggestions.append({"type": "spelling", "text": spell})
            suggestions.append({"type": "tip", "text": "Try removing some filters or broadening your location."})

        return Response({
            "results": JobListSerializer(results, many=True, context={"request": request}).data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "suggestions": suggestions,
        })

    def _expand_synonyms(self, query):
        """Basic synonym expansion (#133)."""
        synonyms = {
            "developer": "engineer|developer|programmer",
            "engineer": "engineer|developer",
            "programmer": "programmer|developer|coder",
            "accountant": "accountant|accounting",
            "marketing": "marketing|digital marketing",
            "sales": "sales|business development",
            "manager": "manager|lead|head",
            "designer": "designer|ui|ux",
            "analyst": "analyst|analytics",
            "teacher": "teacher|lecturer|instructor",
        }
        lower_q = query.lower().strip()
        return synonyms.get(lower_q, query)

    def _spell_correct(self, query):
        """Basic spelling suggestion (#132)."""
        common_misspellings = {
            "softwre": "software", "engneer": "engineer", "devloper": "developer",
            "acountant": "accountant", "managment": "management", "markting": "marketing",
            "colombo": "colombo", "kandy": "kandy", "desinger": "designer",
            "programer": "programmer", "analys": "analyst",
        }
        words = query.lower().split()
        corrected = [common_misspellings.get(w, w) for w in words]
        return " ".join(corrected)


class CompanySearchView(APIView):
    """Company / employer search."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = CompanySearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = EmployerAccount.objects.all().select_related("industry", "headquarters")
        if q := data.get("q"):
            qs = qs.filter(
                Q(company_name__icontains=q) |
                Q(company_name_si__icontains=q) |
                Q(company_name_ta__icontains=q)
            )
        if ind := data.get("industry"):
            qs = qs.filter(industry_id=ind)
        if dist := data.get("district"):
            qs = qs.filter(headquarters_id=dist)
        if data.get("verified_only"):
            qs = qs.filter(is_verified=True)

        sort = data.get("sort", "relevance")
        if sort == "name":
            qs = qs.order_by("company_name")
        elif sort == "jobs":
            qs = qs.order_by("-active_job_count")
        else:
            qs = qs.order_by("-is_verified", "-active_job_count")

        page = data.get("page", 1)
        page_size = data.get("page_size", 20)
        total = qs.count()
        start = (page - 1) * page_size
        results = qs[start:start + page_size]

        return Response({
            "results": EmployerListSerializer(results, many=True).data,
            "total": total,
            "page": page,
            "page_size": page_size,
        })


class SearchSuggestionsView(APIView):
    """Auto-complete / type-ahead suggestions (#87–88)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = SearchSuggestionSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        q = serializer.validated_data["q"]
        lang = serializer.validated_data.get("lang", "en")

        # Job title suggestions
        if lang == "si":
            field = "title_si"
        elif lang == "ta":
            field = "title_ta"
        else:
            field = "title"

        jobs = JobListing.objects.filter(
            status="active", **{f"{field}__icontains": q}
        ).values_list(field, flat=True).distinct()[:5]

        # Company suggestions
        companies = EmployerAccount.objects.filter(
            company_name__icontains=q
        ).values_list("company_name", "slug")[:3]

        # Skill suggestions
        skills = Skill.objects.filter(
            name_en__icontains=q
        ).values_list("name_en", "slug")[:3]

        return Response({
            "job_titles": list(jobs),
            "companies": [{"name": c[0], "slug": c[1]} for c in companies],
            "skills": [{"name": s[0], "slug": s[1]} for s in skills],
        })


class TrendingSearchesView(APIView):
    """Return trending search queries this week (#62)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = "trending_searches"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=7)
        trending = (
            SearchLog.objects.filter(created_at__gte=cutoff, query__gt="")
            .values("query")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        data = [{"query": t["query"], "count": t["count"]} for t in trending]
        cache.set(cache_key, data, 300)  # 5 min cache
        return Response(data)


class RecentSearchesView(APIView):
    """Return user's recent search queries (#75, #89)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recent = (
            SearchLog.objects.filter(user=request.user, query__gt="")
            .order_by("-created_at")
            .values_list("query", flat=True)
            .distinct()[:10]
        )
        return Response(list(recent))


class SearchAnalyticsView(APIView):
    """Search analytics — popular queries, zero-result queries (#135)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        popular = (
            SearchLog.objects.filter(created_at__gte=cutoff, query__gt="")
            .values("query").annotate(count=Count("id"))
            .order_by("-count")[:20]
        )
        zero_results = (
            SearchLog.objects.filter(created_at__gte=cutoff, query__gt="", results_count=0)
            .values("query").annotate(count=Count("id"))
            .order_by("-count")[:20]
        )
        return Response({
            "popular_queries": list(popular),
            "zero_result_queries": list(zero_results),
        })
