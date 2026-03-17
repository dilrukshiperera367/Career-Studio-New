"""CampusOS — Outcomes Analytics serializers."""

from rest_framework import serializers
from .models import AccreditationReport, AlumniDestination, CohortOutcome, EmployabilityTrendPoint, PlacementOutcome


class PlacementOutcomeSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = PlacementOutcome
        fields = "__all__"
        read_only_fields = ["id", "campus", "is_verified", "verified_by"]

    def get_student_name(self, obj):
        return obj.student.get_full_name()


class CohortOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CohortOutcome
        fields = "__all__"
        read_only_fields = ["id", "campus", "computed_at"]


class AlumniDestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlumniDestination
        fields = "__all__"
        read_only_fields = ["id"]


class AccreditationReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccreditationReport
        fields = "__all__"
        read_only_fields = ["id", "campus", "generated_at", "generated_by"]


class EmployabilityTrendPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployabilityTrendPoint
        fields = "__all__"
        read_only_fields = ["id"]
