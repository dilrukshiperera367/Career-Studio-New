"""Taxonomy app — REST API views for skill, title, and location lookup."""

from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SkillTaxonomy, SkillAlias, TitleAlias, LocationAlias


class SkillTaxonomyListView(generics.ListAPIView):
    """
    GET /api/v1/taxonomy/skills/
    Search canonical skill names for autocomplete.
    ?q=pyth → returns matching skills
    ?category=engineering
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["canonical_name"]

    def get_queryset(self):
        qs = SkillTaxonomy.objects.all()
        category = self.request.query_params.get("category")
        q = self.request.query_params.get("q", "").strip()
        if category:
            qs = qs.filter(category=category)
        if q:
            qs = qs.filter(canonical_name__icontains=q)
        return qs.order_by("canonical_name")[:50]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [
            {
                "id": str(s.id),
                "canonical_name": s.canonical_name,
                "category": s.category,
            }
            for s in qs
        ]
        return Response({"count": len(data), "results": data})


class SkillAliasResolveView(APIView):
    """
    POST /api/v1/taxonomy/skills/resolve/
    Body: { "aliases": ["python3", "py", "django"] }
    Returns canonical skill matches.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        aliases = request.data.get("aliases", [])
        if not isinstance(aliases, list):
            return Response({"error": "aliases must be a list"}, status=400)

        results = {}
        for alias in aliases[:50]:  # cap at 50
            normalized = alias.lower().strip()
            # Direct canonical match
            try:
                skill = SkillTaxonomy.objects.get(canonical_name__iexact=normalized)
                results[alias] = {"canonical_name": skill.canonical_name, "category": skill.category, "source": "canonical"}
                continue
            except SkillTaxonomy.DoesNotExist:
                pass
            # Alias match
            try:
                skill_alias = SkillAlias.objects.select_related("skill").get(alias_normalized=normalized)
                skill = skill_alias.skill
                results[alias] = {"canonical_name": skill.canonical_name, "category": skill.category, "source": "alias"}
            except SkillAlias.DoesNotExist:
                results[alias] = None

        return Response(results)


class TitleNormalizeView(APIView):
    """
    POST /api/v1/taxonomy/titles/normalize/
    Body: { "titles": ["Sr Software Eng", "software engineer sr"] }
    Returns canonical title matches.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        titles = request.data.get("titles", [])
        if not isinstance(titles, list):
            return Response({"error": "titles must be a list"}, status=400)

        results = {}
        for title in titles[:50]:
            normalized = title.lower().strip()
            try:
                alias = TitleAlias.objects.get(alias_normalized=normalized)
                results[title] = alias.canonical_title
            except TitleAlias.DoesNotExist:
                results[title] = None

        return Response(results)


class LocationNormalizeView(APIView):
    """
    POST /api/v1/taxonomy/locations/normalize/
    Body: { "locations": ["colombo", "colomob", "COL"] }
    Returns city+country_code.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        locations = request.data.get("locations", [])
        if not isinstance(locations, list):
            return Response({"error": "locations must be a list"}, status=400)

        results = {}
        for loc in locations[:50]:
            normalized = loc.lower().strip()
            try:
                alias = LocationAlias.objects.get(alias_normalized=normalized)
                results[loc] = {"city": alias.city, "country_code": alias.country_code}
            except LocationAlias.DoesNotExist:
                results[loc] = None

        return Response(results)


class SkillCategoryListView(APIView):
    """
    GET /api/v1/taxonomy/skills/categories/
    Returns list of distinct skill categories with counts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        categories = (
            SkillTaxonomy.objects
            .values("category")
            .annotate(count=Count("id"))
            .order_by("category")
        )
        return Response(list(categories))
