"""CampusOS — Students serializers."""

from rest_framework import serializers
from .models import (
    CampusReadinessBadge,
    EmployabilityProfile,
    StudentAchievement,
    StudentActivityLog,
    StudentCertification,
    StudentEducation,
    StudentLanguage,
    StudentProfile,
    StudentProject,
    StudentSkill,
)


class StudentSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentSkill
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEducation
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProject
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCertification
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at", "is_verified"]


class StudentLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentLanguage
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentAchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAchievement
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployabilityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployabilityProfile
        exclude = ["student"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_photo = serializers.ImageField(source="user.profile_photo", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True, default=None)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    campus_name = serializers.CharField(source="campus.name", read_only=True)

    class Meta:
        model = StudentProfile
        fields = "__all__"
        read_only_fields = [
            "id", "user", "campus", "profile_completion_pct",
            "placed_at_company", "placed_package_lkr", "placement_date",
            "created_at", "updated_at",
        ]


class StudentProfileDetailSerializer(StudentProfileSerializer):
    skills = StudentSkillSerializer(many=True, read_only=True)
    educations = StudentEducationSerializer(many=True, read_only=True)
    projects = StudentProjectSerializer(many=True, read_only=True)
    certifications = StudentCertificationSerializer(many=True, read_only=True)
    languages = StudentLanguageSerializer(many=True, read_only=True)
    achievements = StudentAchievementSerializer(many=True, read_only=True)
    employability_profile = EmployabilityProfileSerializer(read_only=True)


class StudentActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentActivityLog
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class CampusReadinessBadgeSerializer(serializers.ModelSerializer):
    issued_by_name = serializers.CharField(
        source="issued_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = CampusReadinessBadge
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "issued_at", "issued_by"]
