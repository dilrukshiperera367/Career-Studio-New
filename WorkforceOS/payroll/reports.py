"""
Bank file & statutory report generators.
- Bank transfer CSV for bulk salary payments
- EPF Return (Form C) — monthly contributions
- ETF Return — monthly employer contributions
- APIT Summary — annual tax deductions
"""

import csv
import io
from datetime import date


def generate_bank_file(payroll_run):
    """Generate bank transfer CSV from a finalized payroll run."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Employee Number', 'Employee Name', 'Bank Name', 'Branch',
        'Account Number', 'Account Type', 'Net Salary (LKR)', 'Reference'
    ])

    for entry in payroll_run.entries.select_related('employee').all():
        bank = entry.employee.bank_details or {}
        writer.writerow([
            entry.employee.employee_number,
            entry.employee.full_name,
            bank.get('bank_name', ''),
            bank.get('branch', ''),
            bank.get('account_no', ''),
            bank.get('account_type', 'savings'),
            f"{float(entry.net_salary):.2f}",
            f"SAL-{payroll_run.period_year}{payroll_run.period_month:02d}-{entry.employee.employee_number}",
        ])

    return output.getvalue()


def generate_epf_return(payroll_run):
    """
    Generate EPF Return (Form C) CSV.
    Monthly report of employee + employer EPF contributions.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'EPF Member No', 'Employee Number', 'Employee Name', 'NIC',
        'Gross Salary', 'EPF Employee (8%)', 'EPF Employer (12%)',
        'Total EPF Contribution'
    ])

    total_ee = total_er = 0

    for entry in payroll_run.entries.select_related('employee').all():
        emp = entry.employee
        epf_ee = float(entry.epf_employee or 0)
        epf_er = float(entry.epf_employer or 0)
        total_ee += epf_ee
        total_er += epf_er

        writer.writerow([
            emp.epf_number if hasattr(emp, 'epf_number') else '',
            emp.employee_number,
            emp.full_name,
            emp.nic_number or '',
            f"{float(entry.gross_salary):.2f}",
            f"{epf_ee:.2f}",
            f"{epf_er:.2f}",
            f"{epf_ee + epf_er:.2f}",
        ])

    # Summary row
    writer.writerow([])
    writer.writerow(['', '', 'TOTAL', '', '', f"{total_ee:.2f}", f"{total_er:.2f}", f"{total_ee + total_er:.2f}"])

    return output.getvalue()


def generate_etf_return(payroll_run):
    """
    Generate ETF Return CSV.
    Monthly report of employer ETF contributions.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Employee Number', 'Employee Name', 'NIC',
        'Gross Salary', 'ETF Employer (3%)'
    ])

    total_etf = 0

    for entry in payroll_run.entries.select_related('employee').all():
        emp = entry.employee
        etf = float(entry.etf_employer or 0)
        total_etf += etf

        writer.writerow([
            emp.employee_number,
            emp.full_name,
            emp.nic_number or '',
            f"{float(entry.gross_salary):.2f}",
            f"{etf:.2f}",
        ])

    writer.writerow([])
    writer.writerow(['', 'TOTAL', '', '', f"{total_etf:.2f}"])

    return output.getvalue()


def generate_apit_summary(payroll_run):
    """
    Generate APIT (income tax) summary CSV.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Employee Number', 'Employee Name', 'NIC',
        'Gross Salary', 'APIT Deducted'
    ])

    total_apit = 0

    for entry in payroll_run.entries.select_related('employee').all():
        emp = entry.employee
        apit = float(entry.apit or 0)
        total_apit += apit

        writer.writerow([
            emp.employee_number,
            emp.full_name,
            emp.nic_number or '',
            f"{float(entry.gross_salary):.2f}",
            f"{apit:.2f}",
        ])

    writer.writerow([])
    writer.writerow(['', 'TOTAL', '', '', f"{total_apit:.2f}"])

    return output.getvalue()


def generate_headcount_report(tenant_id):
    """Generate headcount report CSV."""
    from core_hr.models import Employee

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Employee #', 'Name', 'Department', 'Position', 'Branch',
        'Status', 'Contract', 'Hire Date', 'Gender', 'NIC'
    ])

    employees = Employee.objects.filter(
        tenant_id=tenant_id
    ).select_related('department', 'position', 'branch').order_by('department__name', 'last_name')

    for emp in employees:
        writer.writerow([
            emp.employee_number,
            emp.full_name,
            emp.department.name if emp.department else '',
            emp.position.title if emp.position else '',
            emp.branch.name if emp.branch else '',
            emp.status,
            emp.contract_type,
            emp.hire_date,
            emp.gender,
            emp.nic_number or '',
        ])

    return output.getvalue()


def generate_leave_utilization_report(tenant_id, year):
    """Generate leave utilization report CSV."""
    from leave_attendance.models import LeaveBalance

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Employee #', 'Employee Name', 'Leave Type',
        'Entitled', 'Taken', 'Pending', 'Remaining'
    ])

    balances = LeaveBalance.objects.filter(
        tenant_id=tenant_id, year=year
    ).select_related('employee', 'leave_type').order_by('employee__last_name', 'leave_type__name')

    for b in balances:
        writer.writerow([
            b.employee.employee_number,
            b.employee.full_name,
            b.leave_type.name,
            f"{float(b.entitled):.1f}",
            f"{float(b.taken):.1f}",
            f"{float(b.pending):.1f}",
            f"{float(b.remaining):.1f}",
        ])

    return output.getvalue()


def generate_attendance_report(tenant_id, year, month):
    """Generate attendance summary report CSV."""
    from leave_attendance.models import AttendanceRecord
    from django.db import models as db_models

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Employee #', 'Employee Name', 'Days Present', 'Days Absent',
        'Late Count', 'Total Late (mins)', 'OT Hours'
    ])

    summary = AttendanceRecord.objects.filter(
        tenant_id=tenant_id, date__year=year, date__month=month
    ).values(
        'employee__employee_number', 'employee__first_name', 'employee__last_name'
    ).annotate(
        present=db_models.Count('id', filter=db_models.Q(status='present')),
        absent=db_models.Count('id', filter=db_models.Q(status='absent')),
        late_count=db_models.Count('id', filter=db_models.Q(late_minutes__gt=0)),
        total_late=db_models.Sum('late_minutes'),
        total_ot=db_models.Sum('overtime_hours'),
    ).order_by('employee__last_name')

    for row in summary:
        writer.writerow([
            row['employee__employee_number'],
            f"{row['employee__first_name']} {row['employee__last_name']}",
            row['present'],
            row['absent'],
            row['late_count'],
            row['total_late'] or 0,
            f"{float(row['total_ot'] or 0):.1f}",
        ])

    return output.getvalue()
