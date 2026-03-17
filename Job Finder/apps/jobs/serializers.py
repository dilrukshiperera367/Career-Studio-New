"""Jobs serializers — Job listings, saved jobs, reporting."""
from rest_framework import serializers
from .models import JobListing, SavedJob

# ── Alias: JobListingSerializer kept for backward compat (employer views etc.)
# Full detail version is now JobDetailSerializer.


class SkillSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name_en = serializers.CharField(source="name_en", read_only=True)
    slug = serializers.SlugField(read_only=True)


class JobListSerializer(serializers.ModelSerializer):
    """Lighter serializer for job browse / cards."""
    employer_name = serializers.CharField(source="employer.company_name", read_only=True)
    employer_slug = serializers.CharField(source="employer.slug", read_only=True)
    employer_logo = serializers.ImageField(source="employer.logo", read_only=True)
    employer_is_verified = serializers.BooleanField(source="employer.is_verified", read_only=True)
    district_name = serializers.CharField(source="district.name_en", read_only=True, default="")
    category_name = serializers.SerializerMethodField()
    required_skills = serializers.SerializerMethodField()

    class Meta:
        model = JobListing
        fields = [
            "id", "title", "title_si", "title_ta", "slug",
            "employer", "employer_name", "employer_slug", "employer_logo", "employer_is_verified",
            "district", "district_name", "category", "category_name",
            "job_type", "experience_level", "work_arrangement",
            "salary_min", "salary_max", "salary_currency", "salary_period", "hide_salary",
            "is_featured", "is_boosted", "is_sponsored", "urgent", "status",
            "quick_apply_enabled", "visa_sponsorship",
            "application_count", "view_count",
            "published_at", "expires_at", "application_deadline",
            "quality_score", "freshness_score",
            "required_skills",
        ]

    def get_category_name(self, obj):
        return obj.category.name_en if obj.category else ""

    def get_required_skills(self, obj):
        return [{"name_en": s.name_en, "slug": s.slug} for s in obj.required_skills.all()[:5]]


class EmployerSnapshotSerializer(serializers.Serializer):
    """Inline company snapshot for job detail page."""
    id = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    logo = serializers.ImageField(read_only=True, allow_null=True)
    company_size = serializers.CharField(read_only=True, default="")
    is_verified = serializers.BooleanField(read_only=True)
    website = serializers.URLField(read_only=True, allow_null=True)
    industry_name = serializers.SerializerMethodField()
    headquarters_name = serializers.SerializerMethodField()
    active_job_count = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True, default="")
    founded_year = serializers.IntegerField(read_only=True, allow_null=True)
    overview = serializers.CharField(read_only=True, default="")

    def get_industry_name(self, obj):
        return obj.industry.name_en if obj.industry else ""

    def get_headquarters_name(self, obj):
        return obj.headquarters.name_en if hasattr(obj, 'headquarters') and obj.headquarters else ""


class JobDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for a single job — all fields for the 2.0 detail page."""
    # Employer snapshot
    employer_detail = EmployerSnapshotSerializer(source="employer", read_only=True)

    # Location
    district_name = serializers.CharField(source="district.name_en", read_only=True, default="")
    district_slug = serializers.CharField(source="district.slug", read_only=True, default="")
    province_name = serializers.CharField(source="province.name_en", read_only=True, default="")

    # Classification
    category_name = serializers.CharField(source="category.name_en", read_only=True, default="")
    category_slug = serializers.SlugField(source="category.slug", read_only=True, default="")
    subcategory_name = serializers.CharField(source="subcategory.name_en", read_only=True, default="")
    industry_name = serializers.CharField(source="industry.name_en", read_only=True, default="")

    # Skills
    required_skills = serializers.SerializerMethodField()
    preferred_skills = serializers.SerializerMethodField()

    # Education
    min_education_label = serializers.CharField(source="min_education.name_en", read_only=True, default="")

    # Compensation breakdown
    compensation_breakdown = serializers.SerializerMethodField()

    # Match score (injected by view)
    match_score = serializers.SerializerMethodField()
    matching_skills = serializers.SerializerMethodField()
    missing_skills = serializers.SerializerMethodField()

    # Quality
    quality_score_detail = serializers.SerializerMethodField()

    # Recruiter info
    recruiter_info = serializers.SerializerMethodField()

    class Meta:
        model = JobListing
        fields = [
            # Core identity
            "id", "slug", "title", "title_si", "title_ta",
            # Employer
            "employer", "employer_detail",
            # Trilingual content
            "description", "description_si", "description_ta",
            "requirements", "requirements_si", "requirements_ta",
            "benefits", "benefits_si", "benefits_ta",
            # Location
            "district", "district_name", "district_slug",
            "province", "province_name",
            "address_line", "latitude", "longitude",
            # Classification
            "category", "category_name", "category_slug",
            "subcategory", "subcategory_name",
            "industry", "industry_name",
            "job_type", "experience_level", "work_arrangement",
            "experience_years_min", "experience_years_max",
            # Compensation
            "salary_min", "salary_max", "salary_currency", "salary_period", "hide_salary",
            "compensation_breakdown",
            # Schedule / shift
            "shift_type", "language_requirements",
            # Skills
            "required_skills", "preferred_skills",
            "min_education", "min_education_label",
            # Application
            "apply_method", "external_apply_url", "email_apply_address",
            "quick_apply_enabled", "requires_cover_letter", "requires_resume",
            "screening_questions", "application_deadline",
            # Status & promotion
            "status", "is_featured", "is_boosted", "is_sponsored", "urgent",
            "visa_sponsorship",
            # FAQs
            "structured_faqs",
            # SEO
            "meta_title", "meta_description", "canonical_url",
            # ATS
            "ats_job_id",
            # Stats
            "view_count", "application_count", "share_count",
            "quality_score", "freshness_score",
            "quality_score_detail",
            # Dates
            "published_at", "expires_at", "closed_at",
            "created_at", "updated_at",
            # Computed
            "match_score", "matching_skills", "missing_skills",
            "recruiter_info",
        ]
        read_only_fields = [
            "id", "slug", "view_count", "application_count", "share_count",
            "created_at", "updated_at",
        ]

    def get_required_skills(self, obj):
        return [{"id": str(s.id), "name_en": s.name_en, "slug": s.slug} for s in obj.required_skills.all()]

    def get_preferred_skills(self, obj):
        return [{"id": str(s.id), "name_en": s.name_en, "slug": s.slug} for s in obj.preferred_skills.all()]

    def get_compensation_breakdown(self, obj):
        """Return structured compensation data for the breakdown table."""
        if not obj.salary_min and not obj.salary_max:
            return None
        period = obj.salary_period or "monthly"
        multipliers = {"hourly": 160, "monthly": 1, "annual": 1/12}
        m = multipliers.get(period, 1)
        monthly_min = float(obj.salary_min) * m if obj.salary_min else None
        monthly_max = float(obj.salary_max) * m if obj.salary_max else None
        return {
            "currency": obj.salary_currency,
            "period": period,
            "min": float(obj.salary_min) if obj.salary_min else None,
            "max": float(obj.salary_max) if obj.salary_max else None,
            "monthly_min": round(monthly_min, 0) if monthly_min else None,
            "monthly_max": round(monthly_max, 0) if monthly_max else None,
            "annual_min": round(monthly_min * 12, 0) if monthly_min else None,
            "annual_max": round(monthly_max * 12, 0) if monthly_max else None,
            "hide_salary": obj.hide_salary,
        }

    def get_match_score(self, obj):
        return self.context.get("match_score")

    def get_matching_skills(self, obj):
        return self.context.get("matching_skills", [])

    def get_missing_skills(self, obj):
        return self.context.get("missing_skills", [])

    def get_quality_score_detail(self, obj):
        try:
            qs = obj.quality_score_obj
            return {
                "overall": qs.overall_score,
                "freshness": qs.freshness_score,
                "completeness": qs.completeness_score,
                "trust": qs.trust_score,
                "scam_risk": qs.scam_risk,
                "is_duplicate": qs.is_duplicate,
            }
        except Exception:
            return None

    def get_recruiter_info(self, obj):
        try:
            poster = obj.posted_by
            if not poster:
                return None
            return {
                "name": getattr(poster, "get_full_name", lambda: "")() or poster.email.split("@")[0],
                "response_time": "Usually responds within 3 days",  # Could be real metric
                "hire_rate": None,  # Future: compute from applications
            }
        except Exception:
            return None


class JobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new job listing."""
    class Meta:
        model = JobListing
        fields = [
            "title", "title_si", "title_ta",
            "district", "province", "category", "subcategory", "industry",
            "job_type", "experience_level", "work_arrangement",
            "salary_min", "salary_max", "salary_currency", "salary_period", "hide_salary",
            "description", "description_si", "description_ta",
            "requirements", "requirements_si", "requirements_ta",
            "benefits", "benefits_si", "benefits_ta",
            "min_education", "experience_years_min", "experience_years_max",
            "required_skills", "preferred_skills",
            "apply_method", "external_apply_url", "email_apply_address",
            "screening_questions", "structured_faqs", "language_requirements",
            "quick_apply_enabled", "requires_cover_letter", "requires_resume",
            "visa_sponsorship", "shift_type", "application_deadline",
            "meta_title", "meta_description",
        ]


class SavedJobSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_slug = serializers.CharField(source="job.slug", read_only=True)
    employer_name = serializers.CharField(source="job.employer.company_name", read_only=True)
    employer_logo = serializers.ImageField(source="job.employer.logo", read_only=True, allow_null=True)
    salary_min = serializers.DecimalField(source="job.salary_min", read_only=True, max_digits=12, decimal_places=2, allow_null=True)
    salary_max = serializers.DecimalField(source="job.salary_max", read_only=True, max_digits=12, decimal_places=2, allow_null=True)
    district_name = serializers.CharField(source="job.district.name_en", read_only=True, default="")

    class Meta:
        model = SavedJob
        fields = [
            "id", "job", "job_title", "job_slug", "employer_name", "employer_logo",
            "salary_min", "salary_max", "district_name",
            "saved_at", "notes",
        ]
        read_only_fields = ["id", "saved_at"]


class ReportJobSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=50)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True)


# Backward-compat alias (used by EmployerJobDetailView and other views)
JobListingSerializer = JobDetailSerializer
