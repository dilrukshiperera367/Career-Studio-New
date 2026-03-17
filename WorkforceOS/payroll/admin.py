"""Admin registration for the payroll app."""

from django.contrib import admin
from .models import (
    SalaryStructure, EmployeeCompensation, PayrollRun,
    PayrollEntry, StatutoryRule, LoanRecord, PayrollAuditLog,
)


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'company', 'status', 'created_at')
    list_filter = ('status', 'tenant')
    search_fields = ('name', 'description', 'tenant__name', 'company__name')
    readonly_fields = ('id', 'created_at')


@admin.register(EmployeeCompensation)
class EmployeeCompensationAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'salary_structure', 'basic_salary', 'gross_salary',
                    'currency', 'payment_frequency', 'effective_date', 'is_current', 'created_at')
    list_filter = ('currency', 'payment_frequency', 'is_current', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'tenant__name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('employee',)
    date_hierarchy = 'effective_date'


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'company', 'period_year', 'period_month', 'status',
                    'employee_count', 'total_gross', 'total_net', 'finalized_at', 'created_at')
    list_filter = ('status', 'period_year', 'tenant')
    search_fields = ('name', 'notes', 'tenant__name', 'company__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'finalized_at')
    ordering = ('-period_year', '-period_month')


@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'payroll_run', 'basic_salary', 'total_earnings',
                    'total_deductions', 'net_salary', 'payment_method', 'payslip_sent', 'created_at')
    list_filter = ('payment_method', 'payslip_sent', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'tenant__name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('employee',)


@admin.register(StatutoryRule)
class StatutoryRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'rule_type', 'effective_from', 'effective_to',
                    'version', 'is_active', 'created_at')
    list_filter = ('country', 'rule_type', 'is_active')
    search_fields = ('name', 'country')
    readonly_fields = ('id', 'created_at')
    ordering = ('country', 'rule_type', '-effective_from')


@admin.register(LoanRecord)
class LoanRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'loan_type', 'amount', 'installment_amount',
                    'installments_total', 'installments_paid', 'outstanding_balance',
                    'interest_rate', 'start_date', 'status', 'created_at')
    list_filter = ('loan_type', 'status', 'tenant')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_number',
                     'tenant__name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('employee', 'approved_by')
    date_hierarchy = 'start_date'


@admin.register(PayrollAuditLog)
class PayrollAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'payroll_run', 'action', 'actor', 'ip_address', 'created_at')
    list_filter = ('action', 'tenant')
    search_fields = ('action', 'actor__email', 'ip_address', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'details', 'ip_address')
    date_hierarchy = 'created_at'
