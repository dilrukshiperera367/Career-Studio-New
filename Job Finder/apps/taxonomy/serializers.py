"""Taxonomy serializers — read-only serializers for look-up tables."""
from rest_framework import serializers
from .models import Province, District, JobCategory, JobSubCategory, Industry, Skill, EducationLevel


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ["id", "name_en", "name_si", "name_ta", "slug"]


class DistrictSerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source="province.name_en", read_only=True)

    class Meta:
        model = District
        fields = [
            "id", "name_en", "name_si", "name_ta", "slug",
            "province", "province_name", "latitude", "longitude", "is_active",
        ]


class DistrictMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name_en", "name_si", "name_ta", "slug"]


class JobCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    job_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobCategory
        fields = [
            "id", "name_en", "name_si", "name_ta", "slug", "icon",
            "parent", "sort_order", "job_count", "is_featured", "subcategories",
        ]

    def get_subcategories(self, obj):
        subs = obj.subcategories.all()
        return JobSubCategorySerializer(subs, many=True).data


class JobSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSubCategory
        fields = ["id", "name_en", "name_si", "name_ta", "slug", "category"]


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ["id", "name_en", "name_si", "name_ta", "slug", "naics_code"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name_en", "name_si", "name_ta", "slug", "canonical_name", "category"]


class EducationLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationLevel
        fields = ["id", "code", "name_en", "name_si", "name_ta", "sort_order", "is_sl_specific"]
