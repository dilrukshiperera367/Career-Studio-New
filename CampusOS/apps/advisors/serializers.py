from rest_framework import serializers
from .models import AdvisorProfile, AdvisorStudentMapping, InterventionAlert, ResumeApprovalRequest, StudentNote


class AdvisorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = AdvisorProfile
        fields = "__all__"
        read_only_fields = ["id", "user", "campus"]

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class AdvisorStudentMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvisorStudentMapping
        fields = "__all__"
        read_only_fields = ["id", "assigned_at"]


class StudentNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentNote
        fields = "__all__"
        read_only_fields = ["id", "advisor"]


class ResumeApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeApprovalRequest
        fields = "__all__"
        read_only_fields = ["id", "student", "status", "reviewed_at"]


class InterventionAlertSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = InterventionAlert
        fields = "__all__"
        read_only_fields = ["id"]

    def get_student_name(self, obj):
        return obj.student.get_full_name()
