"""Admin registration for the learning app."""

from django.contrib import admin
from .models import Course, CourseEnrollment, Certification


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'category', 'format', 'provider',
                    'duration_hours', 'max_enrollments', 'status', 'created_at')
    list_filter = ('category', 'format', 'status', 'tenant')
    search_fields = ('title', 'description', 'provider', 'tenant__name')
    readonly_fields = ('id', 'created_at')
    ordering = ('title',)


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'tenant', 'employee', 'status', 'progress',
                    'score', 'enrolled_at', 'completed_at')
    list_filter = ('status', 'tenant')
    search_fields = ('course__title', 'employee__first_name', 'employee__last_name',
                     'employee__employee_number')
    readonly_fields = ('id', 'enrolled_at')
    raw_id_fields = ('employee',)
    date_hierarchy = 'enrolled_at'


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'employee', 'issuing_body', 'credential_id',
                    'issued_date', 'expiry_date', 'status', 'reminder_sent', 'created_at')
    list_filter = ('status', 'reminder_sent', 'tenant')
    search_fields = ('name', 'issuing_body', 'credential_id',
                     'employee__first_name', 'employee__last_name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('employee',)
    date_hierarchy = 'issued_date'
