from rest_framework import serializers
from .models import (
    Course, CourseModule, CourseLesson, CourseEnrollment, CourseCompletion,
    CohortProgram, CohortEnrollment, CourseLearningPath,
)


class CourseLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseLesson
        fields = "__all__"
        read_only_fields = ["id"]


class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = CourseLessonSerializer(many=True, read_only=True)

    class Meta:
        model = CourseModule
        fields = "__all__"
        read_only_fields = ["id"]


class CourseSerializer(serializers.ModelSerializer):
    modules = CourseModuleSerializer(many=True, read_only=True)
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)
    course_type_label = serializers.CharField(source="get_course_type_display", read_only=True)

    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = ["id", "total_enrollments", "average_rating", "completion_rate", "created_at", "updated_at"]


class CourseListSerializer(serializers.ModelSerializer):
    """Lightweight catalog view."""
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "slug", "title", "short_description", "course_type", "difficulty_level",
            "price_lkr", "currency", "is_free", "certificate_awarded",
            "total_enrollments", "average_rating", "duration_hours", "session_count",
            "thumbnail_url", "provider_name", "is_featured", "next_start_date",
        ]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = "__all__"
        read_only_fields = ["id", "progress_pct", "enrolled_at", "last_accessed_at"]


class CourseCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCompletion
        fields = "__all__"
        read_only_fields = ["id", "completed_at"]


class CohortEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CohortEnrollment
        fields = "__all__"
        read_only_fields = ["id", "enrolled_at"]


class CohortProgramSerializer(serializers.ModelSerializer):
    enrollments = CohortEnrollmentSerializer(many=True, read_only=True)
    enrolled_count = serializers.SerializerMethodField()

    class Meta:
        model = CohortProgram
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def get_enrolled_count(self, obj):
        return obj.enrollments.filter(status="active").count()


class CourseLearningPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseLearningPath
        fields = "__all__"
        read_only_fields = ["id", "slug", "created_at"]
