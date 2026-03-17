from rest_framework import serializers
from .models import DigitalBadge, MicroCredential, MicroCredentialEnrollment, SkillEvidenceBundle, StudentBadgeAward, VerifiedCertification


class DigitalBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalBadge
        fields = "__all__"
        read_only_fields = ["id", "campus", "created_by"]


class StudentBadgeAwardSerializer(serializers.ModelSerializer):
    badge_name = serializers.SerializerMethodField()
    badge_image_url = serializers.SerializerMethodField()

    class Meta:
        model = StudentBadgeAward
        fields = "__all__"
        read_only_fields = ["id", "awarded_by", "awarded_at", "assertion_id"]

    def get_badge_name(self, obj):
        return obj.badge.name

    def get_badge_image_url(self, obj):
        return obj.badge.image_url


class VerifiedCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerifiedCertification
        fields = "__all__"
        read_only_fields = ["id", "student", "campus", "is_verified", "verified_by", "verified_at"]


class MicroCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = MicroCredential
        fields = "__all__"
        read_only_fields = ["id", "campus"]


class MicroCredentialEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MicroCredentialEnrollment
        fields = "__all__"
        read_only_fields = ["id", "student"]


class SkillEvidenceBundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillEvidenceBundle
        fields = "__all__"
        read_only_fields = ["id", "student", "endorsements_count"]
