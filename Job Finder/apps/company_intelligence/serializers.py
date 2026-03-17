"""Company Intelligence — serializers."""
from rest_framework import serializers
from .models import CompanyOfficeLocation, CompanyBenefit, CompanyQnA, HiringActivityIndicator, EmployerComparison


class CompanyOfficeLocationSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = CompanyOfficeLocation
        fields = ["id", "name", "address", "district", "district_name", "city",
                  "latitude", "longitude", "is_headquarters", "employee_count", "active_job_count", "photos"]


class CompanyBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBenefit
        fields = ["id", "category", "label", "description", "is_highlighted", "sort_order"]


class CompanyQnASerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyQnA
        fields = ["id", "question", "answer", "is_employer_answer", "helpful_count",
                  "answered_at", "created_at"]
        read_only_fields = ["helpful_count", "answered_at", "is_employer_answer"]


class CompanyQnACreateSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)


class HiringActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = HiringActivityIndicator
        fields = ["week_start", "new_jobs_posted", "jobs_filled", "avg_response_hours",
                  "avg_time_to_hire_days", "open_positions", "is_actively_hiring"]
