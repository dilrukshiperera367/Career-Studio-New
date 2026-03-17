"""Employers serializers — Company profile, team, branding, TalentOS."""
from rest_framework import serializers
from .models import (
    EmployerAccount, EmployerTeamMember, EmployerBranding, EmployerFollow,
    SalaryReport, JobDescription, InterviewKit, InterviewQuestion,
    SilverMedalist, ReferralCampaign, Referral, RecruiterContact,
    CareerSitePage, InterviewDebrief, DebriefFeedback,
)


class EmployerBrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerBranding
        fields = [
            "primary_color", "banner_images", "employee_testimonials",
            "benefits", "office_photos", "video_url", "culture_keywords",
        ]


class EmployerAccountSerializer(serializers.ModelSerializer):
    branding = EmployerBrandingSerializer(read_only=True)

    class Meta:
        model = EmployerAccount
        fields = [
            "id", "company_name", "company_name_si", "company_name_ta", "slug",
            "logo", "cover_image", "website", "description", "description_si",
            "description_ta", "industry", "company_size", "founded_year",
            "headquarters", "registration_no", "is_verified", "verification_badge",
            "linkedin_url", "facebook_url", "twitter_url", "youtube_url",
            "plan", "active_job_count", "avg_rating", "review_count",
            "follower_count", "ats_connected", "branding",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "is_verified", "verification_badge", "plan",
            "active_job_count", "avg_rating", "review_count", "follower_count",
            "ats_connected", "created_at", "updated_at",
        ]


class EmployerAccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerAccount
        fields = [
            "company_name", "company_name_si", "company_name_ta",
            "logo", "cover_image", "website", "description", "description_si",
            "description_ta", "industry", "company_size", "founded_year",
            "headquarters", "registration_no", "tax_id",
            "linkedin_url", "facebook_url", "twitter_url", "youtube_url",
        ]


class EmployerListSerializer(serializers.ModelSerializer):
    """Lighter serializer for company listings / cards."""
    class Meta:
        model = EmployerAccount
        fields = [
            "id", "company_name", "company_name_si", "company_name_ta", "slug",
            "logo", "industry", "company_size", "headquarters",
            "is_verified", "verification_badge", "active_job_count",
            "avg_rating", "review_count",
        ]


class EmployerTeamMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = EmployerTeamMember
        fields = ["id", "user", "email", "role", "invited_at", "accepted_at"]
        read_only_fields = ["id", "invited_at", "accepted_at"]


class TeamMemberInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=EmployerTeamMember.Role.choices, default="recruiter")


class EmployerFollowSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source="employer.company_name", read_only=True)
    employer_slug = serializers.CharField(source="employer.slug", read_only=True)
    employer_logo = serializers.ImageField(source="employer.logo", read_only=True)
    employer_industry = serializers.SerializerMethodField()
    employer_active_jobs = serializers.IntegerField(source="employer.active_job_count", read_only=True)
    employer_verified = serializers.BooleanField(source="employer.is_verified", read_only=True)
    employer_follower_count = serializers.IntegerField(source="employer.follower_count", read_only=True)

    def get_employer_industry(self, obj):
        if obj.employer.industry:
            return obj.employer.industry.name_en
        return None

    class Meta:
        model = EmployerFollow
        fields = [
            "id", "employer", "employer_name", "employer_slug", "employer_logo",
            "employer_industry", "employer_active_jobs", "employer_verified",
            "employer_follower_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SalaryReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryReport
        fields = [
            "id", "job_title", "department", "experience_years",
            "base_salary", "bonus", "total_comp", "currency",
            "is_verified", "created_at",
        ]
        read_only_fields = ["id", "is_verified", "created_at"]


# ── TalentOS Serializers ──────────────────────────────────────────────────────

class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ["id", "employer", "title", "department", "level", "skills",
                  "salary_min", "salary_max", "content", "word_count", "created_at"]
        read_only_fields = ["id", "word_count", "created_at"]

    def create(self, validated_data):
        validated_data["word_count"] = len(validated_data.get("content", "").split())
        return super().create(validated_data)


class InterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewQuestion
        fields = ["id", "category", "question", "expected_answer", "max_score", "sort_order"]
        read_only_fields = ["id"]


class InterviewKitSerializer(serializers.ModelSerializer):
    questions = InterviewQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewKit
        fields = ["id", "employer", "title", "role", "description",
                  "scoring_criteria", "questions", "created_at"]
        read_only_fields = ["id", "created_at"]


class SilverMedalistSerializer(serializers.ModelSerializer):
    class Meta:
        model = SilverMedalist
        fields = ["id", "employer", "candidate", "name", "original_role",
                  "score", "skills", "recruiter_notes", "applied_date",
                  "last_contacted", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = ["id", "campaign", "referred_by", "candidate_name",
                  "candidate_email", "role", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReferralCampaignSerializer(serializers.ModelSerializer):
    referrals = ReferralSerializer(many=True, read_only=True)
    referral_count = serializers.SerializerMethodField()

    class Meta:
        model = ReferralCampaign
        fields = ["id", "employer", "title", "description", "reward_amount",
                  "reward_currency", "is_active", "start_date", "end_date",
                  "referrals", "referral_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_referral_count(self, obj):
        return obj.referrals.count()


class RecruiterContactSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(
        source="district.name_en", read_only=True, default=""
    )

    class Meta:
        model = RecruiterContact
        fields = ["id", "employer", "name", "email", "phone", "role_interest",
                  "source", "stage", "skills", "district", "district_name",
                  "last_contact", "notes", "score", "created_at"]
        read_only_fields = ["id", "created_at"]


class CareerSitePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerSitePage
        fields = ["id", "employer", "company_name", "primary_color",
                  "sections", "is_published", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class DebriefFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebriefFeedback
        fields = ["id", "interviewer_name", "interviewer_role", "score",
                  "recommendation", "notes"]
        read_only_fields = ["id"]


class InterviewDebriefSerializer(serializers.ModelSerializer):
    feedback = DebriefFeedbackSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewDebrief
        fields = ["id", "employer", "candidate_name", "role", "date",
                  "consensus", "status", "feedback", "created_at"]
        read_only_fields = ["id", "created_at"]
