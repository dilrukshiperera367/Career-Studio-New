"""Search serializers — query parameters for search endpoints."""
from rest_framework import serializers


class JobSearchSerializer(serializers.Serializer):
    """Query parameters for the main job search endpoint."""
    q = serializers.CharField(required=False, default="")
    category = serializers.UUIDField(required=False)
    subcategory = serializers.UUIDField(required=False)
    district = serializers.UUIDField(required=False)
    province = serializers.UUIDField(required=False)
    industry = serializers.UUIDField(required=False)
    employer = serializers.UUIDField(required=False)
    job_type = serializers.CharField(required=False, default="")
    experience_level = serializers.CharField(required=False, default="")
    work_arrangement = serializers.CharField(required=False, default="")
    education_level = serializers.CharField(required=False, default="")
    salary_min = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, allow_null=True, default=None)
    salary_max = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, allow_null=True, default=None)
    salary_currency = serializers.CharField(required=False, default="LKR")
    skills = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    language_required = serializers.CharField(required=False, default="")
    company_size = serializers.CharField(required=False, default="")
    # New advanced filters
    visa_sponsorship = serializers.BooleanField(required=False, default=False)
    shift_type = serializers.CharField(required=False, default="")
    contract_type = serializers.CharField(required=False, default="")
    quick_apply = serializers.BooleanField(required=False, default=False)
    remote_only = serializers.BooleanField(required=False, default=False)
    posted_within = serializers.ChoiceField(
        required=False, default="",
        choices=[("", "Any"), ("24h", "24 hours"), ("3d", "3 days"), ("7d", "7 days"), ("30d", "30 days")],
    )
    # Toggle filters
    verified_only = serializers.BooleanField(required=False, default=False)
    salary_shown = serializers.BooleanField(required=False, default=False)
    government_only = serializers.BooleanField(required=False, default=False)
    foreign_only = serializers.BooleanField(required=False, default=False)
    # Sort
    sort = serializers.ChoiceField(
        required=False, default="relevance",
        choices=[
            ("relevance", "Relevance"), ("date", "Newest"),
            ("salary_desc", "Highest Salary"), ("salary_asc", "Lowest Salary"),
            ("closing_date", "Closing Soon"), ("trending", "Trending"),
        ],
    )
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)
    lang = serializers.ChoiceField(required=False, default="en", choices=[("en", "en"), ("si", "si"), ("ta", "ta")])


class CompanySearchSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, default="")
    industry = serializers.UUIDField(required=False)
    district = serializers.UUIDField(required=False)
    verified_only = serializers.BooleanField(required=False, default=False)
    sort = serializers.ChoiceField(
        required=False, default="relevance",
        choices=[("relevance", "Relevance"), ("name", "Name"), ("jobs", "Most Jobs")],
    )
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)


class SearchSuggestionSerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2)
    lang = serializers.ChoiceField(required=False, default="en", choices=[("en", "en"), ("si", "si"), ("ta", "ta")])
