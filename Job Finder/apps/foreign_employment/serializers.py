"""Foreign Employment serializers — SLBFE agencies, overseas jobs, pre-departure."""
from rest_framework import serializers
from .models import ForeignEmploymentAgency, OverseasJob, PreDepartureChecklist


class ForeignEmploymentAgencySerializer(serializers.ModelSerializer):
    active_jobs_count = serializers.SerializerMethodField()

    class Meta:
        model = ForeignEmploymentAgency
        fields = [
            "id", "name", "name_si", "name_ta", "slug",
            "license_number", "license_valid_until",
            "is_slbfe_registered", "is_verified",
            "phone", "email", "website",
            "countries_served", "specializations",
            "rating", "active_jobs_count",
        ]

    def get_active_jobs_count(self, obj):
        return obj.jobs.filter(status="active").count()


class OverseasJobSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    agency_slug = serializers.CharField(source="agency.slug", read_only=True)
    agency_is_verified = serializers.BooleanField(source="agency.is_verified", read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = OverseasJob
        fields = [
            "id", "agency_name", "agency_slug", "agency_is_verified",
            "title", "title_si", "title_ta",
            "description", "country", "city",
            "salary_min", "salary_max", "salary_currency",
            "contract_duration_months", "benefits", "requirements",
            "vacancies", "status", "deadline",
            "slbfe_approval_no", "is_expired", "created_at",
        ]

    def get_is_expired(self, obj):
        from django.utils import timezone
        if obj.deadline:
            return obj.deadline < timezone.now().date()
        return False


class PreDepartureChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreDepartureChecklist
        fields = [
            "id", "country", "title", "title_si", "title_ta",
            "description", "description_si", "description_ta",
            "sort_order", "is_mandatory",
        ]
