"""CampusOS — Campus serializers."""

from rest_framework import serializers
from .models import AcademicYear, Campus, CampusBranch, Department, Program


class CampusListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = ["id", "name", "short_name", "slug", "institution_type", "city", "country", "logo", "status"]


class CampusDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = "__all__"
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class CampusBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusBranch
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ProgramSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Program
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
