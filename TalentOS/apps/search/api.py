"""API for Search app — Candidate search + ranked results + saved searches."""

from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import viewsets
from rest_framework.decorators import action
from django.urls import path
from django.utils import timezone

from apps.accounts.permissions import IsRecruiter, HasTenantAccess
from apps.search.services import search_candidates
from apps.search.ranking import rank_candidates
from apps.search.models import SavedSearch, SearchSegmentAlert


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, default="", allow_blank=True)
    job_id = serializers.UUIDField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_blank=True)
    min_experience = serializers.FloatField(required=False, allow_null=True)
    max_experience = serializers.FloatField(required=False, allow_null=True)
    required_skills = serializers.ListField(child=serializers.CharField(), required=False, default=[])
    page = serializers.IntegerField(required=False, default=1)
    page_size = serializers.IntegerField(required=False, default=25)


class CandidateSearchView(APIView):
    """
    Search and rank candidates.
    POST /api/v1/search/
    """
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def post(self, request):
        ser = SearchRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        filters = {}
        if data.get("location"):
            filters["location"] = data["location"]
        if data.get("min_experience") is not None:
            filters["min_experience"] = data["min_experience"]
        if data.get("max_experience") is not None:
            filters["max_experience"] = data["max_experience"]
        if data.get("required_skills"):
            filters["required_skills"] = data["required_skills"]

        offset = (data["page"] - 1) * data["page_size"]

        # BM25 search from OpenSearch
        search_result = search_candidates(
            tenant_id=str(request.tenant_id),
            query=data.get("query", ""),
            filters=filters,
            size=data["page_size"],
            offset=offset,
        )

        # If job_id provided, apply structured ranking
        if data.get("job_id"):
            from apps.jobs.models import Job
            try:
                job = Job.objects.get(id=data["job_id"], tenant_id=request.tenant_id)
                job_data = {
                    "required_skills": job.required_skills,
                    "optional_skills": job.optional_skills,
                    "target_titles": job.target_titles,
                    "min_years_experience": job.min_years_experience,
                    "max_years_experience": job.max_years_experience,
                    "domain_tags": job.domain_tags,
                }

                # Build candidate data for ranking
                candidates_data = []
                search_scores = {}
                for hit in search_result["hits"]:
                    src = hit["source"]
                    cand_id = hit["candidate_id"]
                    search_scores[cand_id] = hit["score"]
                    candidates_data.append({
                        "candidate_id": cand_id,
                        "most_recent_title": src.get("most_recent_title", ""),
                        "total_experience_years": src.get("total_experience_years"),
                        "recency_score": src.get("recency_score"),
                        "tags": src.get("tags", []),
                        "skill_ids": [s["skill_id"] for s in src.get("skills", [])],
                        "full_name": src.get("full_name", ""),
                        "headline": src.get("headline", ""),
                    })

                ranked = rank_candidates(candidates_data, job_data, search_scores)

                return Response({
                    "total": search_result["total"],
                    "page": data["page"],
                    "page_size": data["page_size"],
                    "results": ranked,
                })

            except Job.DoesNotExist:
                pass

        # Return unranked BM25 results
        return Response({
            "total": search_result["total"],
            "page": data["page"],
            "page_size": data["page_size"],
            "results": search_result["hits"],
        })


# ---------------------------------------------------------------------------
# Saved Searches
# ---------------------------------------------------------------------------

class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = [
            'id', 'name', 'query_json', 'notify_on_match',
            'last_run_at', 'result_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_run_at', 'result_count', 'created_at', 'updated_at']


class SavedSearchListCreateView(ListCreateAPIView):
    """
    GET  /api/v1/search/saved/    — list saved searches for the current user
    POST /api/v1/search/saved/    — create a new saved search
    """
    serializer_class = SavedSearchSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get_queryset(self):
        return SavedSearch.objects.filter(
            tenant_id=self.request.tenant_id,
            user=self.request.user,
        ).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            user=self.request.user,
        )


class SavedSearchDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/search/saved/<pk>/  — retrieve a saved search
    PATCH  /api/v1/search/saved/<pk>/  — update name/query/notify flag
    DELETE /api/v1/search/saved/<pk>/  — delete
    """
    serializer_class = SavedSearchSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get_queryset(self):
        return SavedSearch.objects.filter(
            tenant_id=self.request.tenant_id,
            user=self.request.user,
        )


class SavedSearchRunView(APIView):
    """
    POST /api/v1/search/saved/<pk>/run/
    Re-execute a saved search and update result_count + last_run_at.
    """
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def post(self, request, pk):
        try:
            saved = SavedSearch.objects.get(
                pk=pk, tenant_id=request.tenant_id, user=request.user
            )
        except SavedSearch.DoesNotExist:
            return Response({'error': 'Saved search not found'}, status=status.HTTP_404_NOT_FOUND)

        q = saved.query_json or {}
        filters = {}
        for key in ('location', 'min_experience', 'max_experience', 'required_skills'):
            if q.get(key) is not None:
                filters[key] = q[key]

        result = search_candidates(
            tenant_id=str(request.tenant_id),
            query=q.get('query', ''),
            filters=filters,
            size=25,
            offset=0,
        )

        saved.last_run_at = timezone.now()
        saved.result_count = result.get('total', 0)
        saved.save(update_fields=['last_run_at', 'result_count', 'updated_at'])

        return Response({
            'total': result['total'],
            'results': result['hits'],
            'saved_search': SavedSearchSerializer(saved).data,
        })


class JobMatchView(APIView):
    """
    POST /api/v1/search/match/
    Given a job_id, rank all candidates by match score.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.jobs.models import Job
        from apps.candidates.models import Candidate

        job_id = request.data.get('job_id')
        limit = min(int(request.data.get('limit', 20)), 100)

        if not job_id:
            return Response({'error': 'job_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = Job.objects.get(id=job_id, tenant=request.tenant)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

        required_skills = [s.get('name', '').lower() for s in (job.required_skills or [])]
        min_exp = getattr(job, 'min_experience_years', 0) or 0
        job_title_words = set((job.title or '').lower().split())

        candidates = Candidate.objects.filter(
            tenant=request.tenant,
        ).exclude(status='merged').prefetch_related('skills')[:500]

        results = []
        for candidate in candidates:
            parsed = {
                'total_experience_years': candidate.total_experience_years or 0,
                'recent_title': candidate.most_recent_title or '',
                'recency_score': candidate.recency_score or 0.5,
                'skills': [
                    {'name': s.name} for s in candidate.skills.all()
                ],
            }
            score = self._score(parsed, required_skills, min_exp, job_title_words)
            results.append({
                'candidate_id': str(candidate.id),
                'full_name': candidate.full_name or '',
                'headline': candidate.headline or '',
                'location': candidate.location or '',
                'tags': candidate.tags or [],
                'total_score': score['total'],
                'score_breakdown': score,
            })

        results.sort(key=lambda x: x['total_score'], reverse=True)
        return Response({
            'job_id': str(job.id),
            'job_title': job.title,
            'total_candidates': len(results),
            'results': results[:limit],
        })

    def _score(self, parsed, required_skills, min_exp, job_title_words):
        # Skill match (0-40)
        cand_skills = [s.get('name', '').lower() if isinstance(s, dict) else str(s).lower()
                       for s in (parsed.get('skills') or [])]
        if required_skills:
            matched = sum(1 for rs in required_skills if any(rs in cs for cs in cand_skills))
            skill_score = min(40, int((matched / len(required_skills)) * 40))
        else:
            skill_score = 20

        # Experience (0-25)
        total_years = float(parsed.get('total_experience_years') or 0)
        if min_exp > 0:
            exp_score = min(25, int((min(total_years, min_exp * 2) / (min_exp * 2)) * 25))
        else:
            exp_score = min(25, int(total_years * 2))

        # Title match (0-20)
        recent_title = (parsed.get('recent_title') or '').lower()
        title_score = min(20, len(set(recent_title.split()) & job_title_words) * 7)

        # Recency (0-15)
        recency = float(parsed.get('recency_score') or 0.5)
        recency_score = int(recency * 15)

        total = skill_score + exp_score + title_score + recency_score
        return {
            'total': total,
            'skill_match': skill_score,
            'experience_fit': exp_score,
            'title_match': title_score,
            'recency': recency_score,
        }


# ---------------------------------------------------------------------------
# Search Segment Alerts
# ---------------------------------------------------------------------------

class SearchSegmentAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchSegmentAlert
        fields = [
            "id", "owner", "name", "segment_query", "alert_type",
            "threshold", "status", "last_checked_at", "last_triggered_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner", "last_checked_at", "last_triggered_at", "created_at", "updated_at"]


class SearchSegmentAlertListCreateView(ListCreateAPIView):
    """
    GET  /api/v1/search/segment-alerts/  — list alerts for the current user
    POST /api/v1/search/segment-alerts/  — create a new alert
    """
    serializer_class = SearchSegmentAlertSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return SearchSegmentAlert.objects.filter(
            tenant_id=self.request.tenant_id,
            owner=self.request.user,
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, owner=self.request.user)


class SearchSegmentAlertDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/v1/search/segment-alerts/<pk>/
    """
    serializer_class = SearchSegmentAlertSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get_queryset(self):
        return SearchSegmentAlert.objects.filter(
            tenant_id=self.request.tenant_id,
            owner=self.request.user,
        )


class SearchSegmentAlertDismissView(APIView):
    """
    POST /api/v1/search/segment-alerts/<pk>/dismiss/
    Dismiss a triggered alert.
    """
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def post(self, request, pk):
        try:
            alert = SearchSegmentAlert.objects.get(
                pk=pk, tenant_id=request.tenant_id, owner=request.user
            )
        except SearchSegmentAlert.DoesNotExist:
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)
        alert.status = "dismissed"
        alert.save(update_fields=["status", "updated_at"])
        return Response(SearchSegmentAlertSerializer(alert).data)


urlpatterns = [
    path("", CandidateSearchView.as_view(), name="candidate-search"),
    path("match/", JobMatchView.as_view(), name="job-match"),
    path("saved/", SavedSearchListCreateView.as_view(), name="saved-search-list"),
    path("saved/<uuid:pk>/", SavedSearchDetailView.as_view(), name="saved-search-detail"),
    path("saved/<uuid:pk>/run/", SavedSearchRunView.as_view(), name="saved-search-run"),
    path("segment-alerts/", SearchSegmentAlertListCreateView.as_view(), name="segment-alert-list"),
    path("segment-alerts/<uuid:pk>/", SearchSegmentAlertDetailView.as_view(), name="segment-alert-detail"),
    path("segment-alerts/<uuid:pk>/dismiss/", SearchSegmentAlertDismissView.as_view(), name="segment-alert-dismiss"),
]
