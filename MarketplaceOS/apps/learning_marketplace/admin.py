from django.contrib import admin
from .models import Course, CourseEnrollment, CohortProgram, CohortEnrollment, CourseLearningPath


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "course_type", "status", "price_lkr", "total_enrollments", "average_rating", "is_featured"]
    list_filter = ["course_type", "status", "difficulty_level", "is_free", "is_featured", "certificate_awarded"]
    search_fields = ["title", "provider__display_name"]
    readonly_fields = ["id", "total_enrollments", "average_rating", "completion_rate", "created_at", "updated_at"]


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["learner", "course", "status", "progress_pct", "enrolled_at"]
    list_filter = ["status"]
    search_fields = ["learner__email", "course__title"]


@admin.register(CohortProgram)
class CohortProgramAdmin(admin.ModelAdmin):
    list_display = ["course", "name", "status", "max_participants", "start_date", "end_date"]
    list_filter = ["status"]


@admin.register(CourseLearningPath)
class CourseLearningPathAdmin(admin.ModelAdmin):
    list_display = ["name", "target_role", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
