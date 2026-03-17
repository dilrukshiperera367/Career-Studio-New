"""Admin registration for the core_hr app."""

from django.contrib import admin
from .models import (
    Company, Branch, Department, Position,
    Employee, JobHistory, EmployeeDocument, Announcement,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'legal_name', 'country', 'currency', 'status', 'created_at']
    list_filter = ['status', 'country', 'currency']
    search_fields = ['name', 'legal_name', 'registration_no', 'tax_id']
    ordering = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'country', 'timezone', 'status']
    list_filter = ['status', 'country', 'company']
    search_fields = ['name', 'code']
    ordering = ['company__name', 'name']
    readonly_fields = ['id', 'created_at']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'parent', 'head', 'status']
    list_filter = ['status', 'company']
    search_fields = ['name', 'code']
    ordering = ['name']
    readonly_fields = ['id', 'created_at']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'department', 'grade', 'band', 'headcount', 'status']
    list_filter = ['status', 'department', 'grade']
    search_fields = ['title', 'code', 'grade']
    ordering = ['title']
    readonly_fields = ['id', 'created_at']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_number', 'first_name', 'last_name', 'work_email',
        'department', 'position', 'contract_type', 'status', 'hire_date',
    ]
    list_filter = ['status', 'contract_type', 'employment_type', 'gender', 'company', 'department']
    search_fields = [
        'employee_number', 'first_name', 'last_name',
        'work_email', 'personal_email', 'nic_number', 'mobile_phone',
    ]
    ordering = ['last_name', 'first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['manager', 'department', 'branch', 'position', 'company', 'user']
    date_hierarchy = 'hire_date'
    fieldsets = (
        ('Identity', {'fields': ('id', 'employee_number', 'tenant', 'company', 'user')}),
        ('Personal', {'fields': (
            'first_name', 'last_name', 'preferred_name',
            'date_of_birth', 'gender', 'marital_status',
            'nationality', 'nic_number', 'passport_number', 'photo_url',
        )}),
        ('Contact', {'fields': (
            'work_email', 'personal_email', 'mobile_phone', 'home_phone',
        )}),
        ('Employment', {'fields': (
            'department', 'branch', 'position', 'manager',
            'hire_date', 'confirmation_date',
            'contract_type', 'contract_end_date',
            'employment_type', 'work_schedule',
            'notice_period_days', 'probation_months',
        )}),
        ('Status', {'fields': (
            'status', 'separation_date', 'separation_type', 'separation_reason',
        )}),
        ('Audit', {'fields': ('source', 'ats_candidate_id', 'created_by', 'created_at', 'updated_at')}),
    )


@admin.register(JobHistory)
class JobHistoryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'change_type', 'effective_date', 'new_position', 'new_department', 'approved_by']
    list_filter = ['change_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_number']
    ordering = ['-effective_date']
    readonly_fields = ['id', 'created_at']


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'employee', 'category', 'e_sign_status', 'expiry_date', 'visibility', 'created_at']
    list_filter = ['category', 'e_sign_status', 'visibility']
    search_fields = ['title', 'employee__first_name', 'employee__last_name', 'employee__employee_number']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'is_published', 'pinned', 'published_at', 'expires_at']
    list_filter = ['is_published', 'pinned', 'read_receipt_enabled']
    search_fields = ['title', 'body']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
