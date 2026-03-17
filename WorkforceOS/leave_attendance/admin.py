"""Admin registration for the leave_attendance app."""

from django.contrib import admin
from .models import (
    LeaveType, LeaveBalance, LeaveRequest,
    HolidayCalendar, Holiday,
    ShiftTemplate, ShiftAssignment,
    AttendanceRecord, OvertimeRecord,
)


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'tenant', 'paid', 'max_days_per_year', 'carry_forward',
                    'accrual_type', 'allow_half_day', 'sort_order', 'status', 'created_at')
    list_filter = ('paid', 'carry_forward', 'encashable', 'accrual_type', 'status', 'tenant')
    search_fields = ('name', 'code', 'tenant__name')
    readonly_fields = ('id', 'created_at')
    ordering = ('sort_order', 'name')


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'leave_type', 'year', 'entitled',
                    'taken', 'pending', 'carried_forward', 'adjustment')
    list_filter = ('year', 'leave_type', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'leave_type__name', 'tenant__name')
    readonly_fields = ('id',)
    raw_id_fields = ('employee',)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'tenant', 'leave_type', 'start_date', 'end_date',
                    'days', 'is_half_day', 'status', 'approved_by', 'created_at')
    list_filter = ('status', 'leave_type', 'is_half_day', 'is_short_leave', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'reason', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'approved_at')
    raw_id_fields = ('employee', 'approved_by')
    date_hierarchy = 'start_date'


@admin.register(HolidayCalendar)
class HolidayCalendarAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'year', 'country', 'created_at')
    list_filter = ('year', 'country', 'tenant')
    search_fields = ('name', 'tenant__name')
    readonly_fields = ('id', 'created_at')


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'calendar', 'date', 'type', 'is_optional')
    list_filter = ('type', 'is_optional', 'calendar')
    search_fields = ('name', 'calendar__name')
    readonly_fields = ('id',)
    date_hierarchy = 'date'


@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'tenant', 'start_time', 'end_time', 'break_minutes',
                    'grace_minutes', 'working_hours', 'is_night_shift', 'status', 'created_at')
    list_filter = ('is_night_shift', 'status', 'tenant')
    search_fields = ('name', 'code', 'tenant__name')
    readonly_fields = ('id', 'created_at')


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'tenant', 'shift', 'date', 'is_default', 'day_of_week')
    list_filter = ('is_default', 'shift', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number')
    readonly_fields = ('id',)
    raw_id_fields = ('employee',)
    date_hierarchy = 'date'


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'date', 'shift', 'status', 'clock_in', 'clock_out',
                    'working_hours', 'overtime_hours', 'late_minutes', 'regularized', 'created_at')
    list_filter = ('status', 'clock_in_source', 'exception_type', 'regularized', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'notes', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('employee', 'regularized_by')
    date_hierarchy = 'date'


@admin.register(OvertimeRecord)
class OvertimeRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'date', 'hours', 'rate_multiplier', 'status', 'approved_by', 'created_at')
    list_filter = ('status', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number', 'reason')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('employee', 'approved_by')
    date_hierarchy = 'date'
