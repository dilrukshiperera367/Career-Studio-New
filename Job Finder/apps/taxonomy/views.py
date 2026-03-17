"""Taxonomy views — Read-only lookups for provinces, districts, categories, etc."""
from rest_framework import generics, permissions, filters
from .models import Province, District, JobCategory, JobSubCategory, Industry, Skill, EducationLevel
from .serializers import (
    ProvinceSerializer, DistrictSerializer, JobCategorySerializer,
    JobSubCategorySerializer, IndustrySerializer, SkillSerializer,
    EducationLevelSerializer,
)


class ProvinceListView(generics.ListAPIView):
    queryset = Province.objects.all()
    serializer_class = ProvinceSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class DistrictListView(generics.ListAPIView):
    serializer_class = DistrictSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = District.objects.filter(is_active=True).select_related("province")
        province = self.request.query_params.get("province")
        if province:
            qs = qs.filter(province_id=province)
        return qs


class JobCategoryListView(generics.ListAPIView):
    serializer_class = JobCategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = JobCategory.objects.prefetch_related("subcategories")
        featured = self.request.query_params.get("featured")
        if featured == "true":
            qs = qs.filter(is_featured=True)
        parent = self.request.query_params.get("parent")
        if parent:
            qs = qs.filter(parent_id=parent)
        else:
            qs = qs.filter(parent__isnull=True)
        return qs.order_by("sort_order")


class JobCategoryDetailView(generics.RetrieveAPIView):
    queryset = JobCategory.objects.prefetch_related("subcategories")
    serializer_class = JobCategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


class JobSubCategoryListView(generics.ListAPIView):
    serializer_class = JobSubCategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = JobSubCategory.objects.all()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)
        return qs


class IndustryListView(generics.ListAPIView):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class SkillListView(generics.ListAPIView):
    serializer_class = SkillSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name_en", "name_si", "name_ta", "canonical_name"]

    def get_queryset(self):
        qs = Skill.objects.all()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class EducationLevelListView(generics.ListAPIView):
    queryset = EducationLevel.objects.all().order_by("sort_order")
    serializer_class = EducationLevelSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
