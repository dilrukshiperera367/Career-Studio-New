"""Candidates serializers - seeker profile, resume, skills, experience, education."""
from datetime import date
import os

from django.conf import settings
from rest_framework import serializers

from .models import (
    SeekerProfile,
    SeekerResume,
    SeekerSkill,
    SeekerExperience,
    SeekerEducation,
    SeekerCertification,
    SeekerLanguage,
    SeekerReference,
    SeekerPortfolio,
)


class SeekerSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name_en", read_only=True)

    class Meta:
        model = SeekerSkill
        fields = [
            "id",
            "skill",
            "skill_name",
            "proficiency",
            "years_used",
            "is_verified",
            "verified_at",
            "endorsed_count",
        ]
        read_only_fields = ["id", "is_verified", "verified_at", "endorsed_count"]


class SeekerExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeekerExperience
        fields = [
            "id",
            "company_name",
            "company_link",
            "title",
            "description",
            "district",
            "start_date",
            "end_date",
            "is_current",
            "employment_type",
            "gap_explanation",
            "sort_order",
        ]
        read_only_fields = ["id"]


class SeekerEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeekerEducation
        fields = [
            "id",
            "institution",
            "level",
            "field_of_study",
            "degree_class",
            "grade",
            "start_year",
            "end_year",
            "is_current",
            "sort_order",
        ]
        read_only_fields = ["id"]


class SeekerCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeekerCertification
        fields = [
            "id",
            "name",
            "issuing_org",
            "issue_date",
            "expiry_date",
            "credential_id",
            "credential_url",
        ]
        read_only_fields = ["id"]


class SeekerLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeekerLanguage
        fields = ["id", "language", "proficiency"]
        read_only_fields = ["id"]


class SeekerReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeekerReference
        fields = ["id", "name", "company", "position", "phone", "email", "relationship"]
        read_only_fields = ["id"]


class SeekerPortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeekerPortfolio
        fields = [
            "id",
            "title",
            "description",
            "url",
            "file",
            "file_type",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "file_type"]


class SeekerResumeSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size = serializers.IntegerField(source="file_size_bytes", read_only=True)
    created_at = serializers.DateTimeField(source="uploaded_at", read_only=True)
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = SeekerResume
        fields = [
            "id",
            "title",
            "file",
            "file_url",
            "original_filename",
            "file_type",
            "file_size",
            "parse_status",
            "detected_language",
            "quality_score",
            "quality_tips",
            "is_primary",
            "is_confidential",
            "privacy",
            "include_photo",
            "version_number",
            "view_count",
            "created_at",
            "updated_at",
            "refreshed_at",
        ]
        read_only_fields = [
            "id",
            "original_filename",
            "file_type",
            "file_size",
            "parse_status",
            "detected_language",
            "quality_score",
            "quality_tips",
            "version_number",
            "view_count",
            "created_at",
            "updated_at",
            "refreshed_at",
        ]

    def validate_file(self, file_obj):
        max_size = int(getattr(settings, "MAX_RESUME_FILE_SIZE", 5 * 1024 * 1024))
        if file_obj.size > max_size:
            raise serializers.ValidationError("Resume file must be 5MB or smaller.")

        # Strict MIME checking (#269)
        allowed_mime_types = {
            "application/pdf": "pdf",
            "application/msword": "doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        }
        content_type = getattr(file_obj, "content_type", "") or ""
        extension = os.path.splitext(file_obj.name)[1].lower().lstrip(".")
        if content_type not in allowed_mime_types:
            raise serializers.ValidationError("Unsupported file MIME type. Allowed: PDF, DOC, DOCX.")
        if allowed_mime_types[content_type] != extension:
            raise serializers.ValidationError("File extension does not match MIME type.")
        return file_obj

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST":
            seeker = getattr(request.user, "seeker_profile", None)
            if seeker and seeker.resumes.count() >= 5:
                raise serializers.ValidationError("Maximum 5 resumes allowed.")
        return attrs

    def create(self, validated_data):
        file_obj = validated_data["file"]
        validated_data["original_filename"] = file_obj.name
        validated_data["file_size_bytes"] = file_obj.size
        validated_data["file_type"] = os.path.splitext(file_obj.name)[1].lower().lstrip(".")
        resume = super().create(validated_data)
        if resume.seeker.resumes.count() == 1:
            resume.is_primary = True
            resume.save(update_fields=["is_primary"])
        elif resume.is_primary:
            resume.seeker.resumes.exclude(pk=resume.pk).update(is_primary=False)
        return resume

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if instance.is_primary:
            instance.seeker.resumes.exclude(pk=instance.pk).update(is_primary=False)
        return instance

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return ""
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def get_updated_at(self, obj):
        return obj.refreshed_at or obj.uploaded_at


class SeekerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True, allow_null=True)
    district_name = serializers.CharField(source="district.name_en", read_only=True, default="")
    expected_salary_min = serializers.IntegerField(source="min_salary_expected", read_only=True)
    expected_salary_max = serializers.IntegerField(source="max_salary_expected", read_only=True)
    is_open_to_relocation = serializers.BooleanField(source="willing_to_relocate", read_only=True)
    is_available_immediately = serializers.SerializerMethodField()
    website = serializers.URLField(source="website_url", read_only=True)
    address_line_1 = serializers.CharField(source="address", read_only=True)
    address_line_2 = serializers.SerializerMethodField()
    profile_strength = serializers.SerializerMethodField()
    wizard_progress = serializers.SerializerMethodField()
    suggestions = serializers.SerializerMethodField()

    skills = SeekerSkillSerializer(many=True, read_only=True)
    experiences = SeekerExperienceSerializer(many=True, read_only=True)
    education = SeekerEducationSerializer(many=True, read_only=True)
    certifications = SeekerCertificationSerializer(many=True, read_only=True)
    languages = SeekerLanguageSerializer(many=True, read_only=True)
    references = SeekerReferenceSerializer(many=True, read_only=True)
    portfolio_items = SeekerPortfolioSerializer(many=True, read_only=True)
    resumes = SeekerResumeSerializer(many=True, read_only=True)

    class Meta:
        model = SeekerProfile
        fields = [
            "id",
            "user",
            "email",
            "phone",
            "first_name",
            "last_name",
            "first_name_si",
            "first_name_ta",
            "last_name_si",
            "last_name_ta",
            "headline",
            "headline_si",
            "headline_ta",
            "bio",
            "bio_si",
            "bio_ta",
            "avatar",
            "date_of_birth",
            "gender",
            "nic_number",
            "phone_secondary",
            "district",
            "district_name",
            "city",
            "address",
            "address_line_1",
            "address_line_2",
            "show_email",
            "show_phone",
            "preferred_contact",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "website_url",
            "website",
            "video_intro_url",
            "driving_license",
            "highest_education",
            "ol_results",
            "al_results",
            "al_stream",
            "al_zscore",
            "university",
            "degree_title",
            "desired_job_types",
            "desired_industries",
            "desired_locations",
            "min_salary_expected",
            "max_salary_expected",
            "expected_salary_min",
            "expected_salary_max",
            "willing_to_relocate",
            "is_open_to_relocation",
            "relocation_districts",
            "open_to_remote",
            "available_from",
            "is_available_immediately",
            "job_search_status",
            "profile_visibility",
            "blocked_companies",
            "wizard_step",
            "wizard_completed",
            "wizard_progress",
            "profile_completeness",
            "profile_strength",
            "suggestions",
            "last_profile_edit",
            "ats_candidate_id",
            "skills",
            "experiences",
            "education",
            "certifications",
            "languages",
            "references",
            "portfolio_items",
            "resumes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "email",
            "phone",
            "profile_completeness",
            "profile_strength",
            "wizard_progress",
            "suggestions",
            "last_profile_edit",
            "ats_candidate_id",
            "created_at",
            "updated_at",
        ]

    def get_is_available_immediately(self, obj):
        return not obj.available_from or obj.available_from <= date.today()

    def get_profile_strength(self, obj):
        score = obj.compute_completeness()
        if score < 40:
            return "red"
        if score <= 70:
            return "yellow"
        return "green"

    def get_wizard_progress(self, obj):
        current = max(1, min(obj.wizard_step, 5))
        return f"Step {current} of 5"

    def get_suggestions(self, obj):
        return obj.get_suggestions()

    def get_address_line_2(self, obj):
        return ""


class SeekerProfileUpdateSerializer(serializers.ModelSerializer):
    expected_salary_min = serializers.IntegerField(source="min_salary_expected", required=False, allow_null=True)
    expected_salary_max = serializers.IntegerField(source="max_salary_expected", required=False, allow_null=True)
    preferred_job_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    preferred_work_arrangement = serializers.CharField(write_only=True, required=False, allow_blank=True)
    is_open_to_relocation = serializers.BooleanField(source="willing_to_relocate", required=False)
    is_available_immediately = serializers.BooleanField(write_only=True, required=False)
    website = serializers.URLField(source="website_url", required=False, allow_blank=True)
    address_line_1 = serializers.CharField(source="address", required=False, allow_blank=True)
    address_line_2 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = SeekerProfile
        fields = [
            "first_name",
            "last_name",
            "first_name_si",
            "last_name_si",
            "first_name_ta",
            "last_name_ta",
            "headline",
            "headline_si",
            "headline_ta",
            "bio",
            "bio_si",
            "bio_ta",
            "avatar",
            "date_of_birth",
            "gender",
            "nic_number",
            "district",
            "city",
            "address",
            "address_line_1",
            "address_line_2",
            "phone_secondary",
            "show_email",
            "show_phone",
            "preferred_contact",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "website_url",
            "website",
            "video_intro_url",
            "driving_license",
            "highest_education",
            "ol_results",
            "al_results",
            "al_stream",
            "al_zscore",
            "university",
            "degree_title",
            "desired_job_types",
            "desired_industries",
            "desired_locations",
            "min_salary_expected",
            "max_salary_expected",
            "expected_salary_min",
            "expected_salary_max",
            "willing_to_relocate",
            "is_open_to_relocation",
            "relocation_districts",
            "open_to_remote",
            "available_from",
            "is_available_immediately",
            "job_search_status",
            "profile_visibility",
            "blocked_companies",
            "wizard_step",
            "wizard_completed",
            "preferred_job_type",
            "preferred_work_arrangement",
        ]

    def validate_bio(self, value):
        if len(value.split()) > 500:
            raise serializers.ValidationError("Bio must be 500 words or fewer.")
        return value

    def update(self, instance, validated_data):
        available_immediately = validated_data.pop("is_available_immediately", None)
        preferred_job_type = validated_data.pop("preferred_job_type", "")
        preferred_work_arrangement = validated_data.pop("preferred_work_arrangement", "")
        if preferred_job_type:
            types = list(instance.desired_job_types or [])
            if preferred_job_type not in types:
                types.append(preferred_job_type)
            validated_data["desired_job_types"] = types
        if preferred_work_arrangement:
            validated_data["open_to_remote"] = preferred_work_arrangement in ("remote", "hybrid")

        instance = super().update(instance, validated_data)
        if available_immediately is True:
            instance.available_from = None
            instance.save(update_fields=["available_from", "updated_at"])
        instance.compute_completeness()
        instance.save(update_fields=["profile_completeness", "updated_at"])
        return instance


class ProfileCompletenessSerializer(serializers.Serializer):
    profile_completeness = serializers.IntegerField()
    profile_strength = serializers.CharField()
    suggestions = serializers.ListField(child=serializers.CharField())


class WizardStepSerializer(serializers.Serializer):
    wizard_step = serializers.IntegerField(min_value=1, max_value=6)
    wizard_completed = serializers.BooleanField(required=False)
