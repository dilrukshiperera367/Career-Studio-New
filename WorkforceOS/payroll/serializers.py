"""Payroll serializers."""

from rest_framework import serializers
from config.base_api import TenantSerializerMixin
from .models import (
    SalaryStructure, EmployeeCompensation, PayrollRun,
    PayrollEntry, LoanRecord, StatutoryRule,
)


class SalaryStructureSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class EmployeeCompensationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    structure_name = serializers.CharField(source='salary_structure.name', read_only=True, allow_null=True)

    class Meta:
        model = EmployeeCompensation
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class PayrollRunSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = PayrollRun
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'employee_count', 'total_gross',
                           'total_deductions', 'total_net', 'total_employer_cost',
                           'finalized_at', 'created_at', 'updated_at']


class PayrollEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)

    class Meta:
        model = PayrollEntry
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class LoanRecordSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = LoanRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']
