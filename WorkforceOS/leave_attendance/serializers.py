"""Leave & Attendance serializers."""

from rest_framework import serializers
from config.base_api import TenantSerializerMixin
from .models import (
    LeaveType, LeaveBalance, LeaveRequest, HolidayCalendar, Holiday,
    ShiftTemplate, ShiftAssignment, AttendanceRecord, OvertimeRecord,
)


class LeaveTypeSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    leave_type_color = serializers.CharField(source='leave_type.color', read_only=True)
    remaining = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = '__all__'
        read_only_fields = ['id', 'tenant']


class LeaveRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'status', 'approved_by', 'approved_at',
                           'rejection_reason', 'created_at', 'updated_at']

    def get_approved_by_name(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None


class HolidayCalendarSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    holidays = serializers.SerializerMethodField()

    class Meta:
        model = HolidayCalendar
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_holidays(self, obj):
        return HolidaySerializer(obj.holidays.all(), many=True).data


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'
        read_only_fields = ['id']


class ShiftTemplateSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ShiftTemplate
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    shift_name = serializers.CharField(source='shift.name', read_only=True, allow_null=True)

    class Meta:
        model = AttendanceRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class ClockInSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=['web', 'mobile', 'qr'], default='web')
    location = serializers.JSONField(required=False, allow_null=True)
    photo_url = serializers.URLField(required=False, allow_blank=True)


class ClockOutSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=['web', 'mobile', 'qr'], default='web')
    location = serializers.JSONField(required=False, allow_null=True)


class ShiftAssignmentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    shift_name = serializers.CharField(source='shift.name', read_only=True)

    class Meta:
        model = ShiftAssignment
        fields = '__all__'
        read_only_fields = ['id', 'tenant']


class OvertimeRecordSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = OvertimeRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'status', 'approved_by', 'created_at']
