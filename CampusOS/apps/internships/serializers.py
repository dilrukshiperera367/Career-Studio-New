"""CampusOS — Internships serializers."""

from rest_framework import serializers
from .models import (
    ExperientialEnrollment,
    ExperientialProgram,
    InternshipApplication,
    InternshipLogbook,
    InternshipOpportunity,
    InternshipRecord,
    SupervisorEvaluation,
    TrainingAgreement,
)


class InternshipOpportunitySerializer(serializers.ModelSerializer):
    employer_display = serializers.SerializerMethodField()

    class Meta:
        model = InternshipOpportunity
        fields = "__all__"
        read_only_fields = ["id", "campus", "views_count", "applications_count", "created_at", "updated_at"]

    def get_employer_display(self, obj):
        return obj.employer_name or (obj.employer.name if obj.employer else "")


class InternshipApplicationSerializer(serializers.ModelSerializer):
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = InternshipApplication
        fields = "__all__"
        read_only_fields = [
            "id", "faculty_approved", "faculty_approver",
            "offer_date", "created_at", "updated_at",
        ]


class InternshipLogbookSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternshipLogbook
        exclude = ["record"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupervisorEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupervisorEvaluation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TrainingAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingAgreement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "signed_at"]


class InternshipRecordSerializer(serializers.ModelSerializer):
    logbook_count = serializers.IntegerField(source="logbook_entries.count", read_only=True)
    evaluation_count = serializers.IntegerField(source="evaluations.count", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = InternshipRecord
        fields = "__all__"
        read_only_fields = ["id", "campus", "created_at", "updated_at"]


class ExperientialProgramSerializer(serializers.ModelSerializer):
    enrollment_count = serializers.IntegerField(source="enrollments.count", read_only=True)

    class Meta:
        model = ExperientialProgram
        fields = "__all__"
        read_only_fields = ["id", "campus", "created_at", "updated_at"]


class ExperientialEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperientialEnrollment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
