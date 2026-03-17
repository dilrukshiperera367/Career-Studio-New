"""Salary Intelligence — serializers."""
from rest_framework import serializers
from .models import SalaryEstimate, SalaryBenchmark, SalaryTrend, CostOfLivingIndex, SalarySubmission


class SalaryEstimateSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)

    class Meta:
        model = SalaryEstimate
        fields = ["id", "normalized_title", "district", "district_name", "industry",
                  "experience_level", "salary_p10_lkr", "salary_p25_lkr", "salary_median_lkr",
                  "salary_p75_lkr", "salary_p90_lkr", "sample_size", "confidence_score",
                  "currency", "salary_period", "calculated_at"]


class SalaryBenchmarkSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)

    class Meta:
        model = SalaryBenchmark
        fields = ["id", "title", "district_name", "user_salary", "market_median",
                  "percentile_rank", "below_market", "above_market"]


class SalaryTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryTrend
        fields = ["month", "median_salary_lkr", "sample_size"]


class SalarySubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalarySubmission
        fields = ["id", "normalized_title", "district", "experience_years", "experience_level",
                  "base_salary_lkr", "total_comp_lkr", "has_bonus", "has_medical", "job_type",
                  "gender", "created_at"]
        read_only_fields = ["id", "created_at", "verification_status"]
