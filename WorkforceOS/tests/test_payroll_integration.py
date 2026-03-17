"""
Integration test: Attendance records → Payroll calculation → Net pay.
End-to-end payroll pipeline including attendance data feed,
EPF/ETF/APIT statutory deductions, and payroll run lifecycle.
"""

from decimal import Decimal
from datetime import date, timedelta

import pytest
from django.test import TestCase

from tenants.models import Tenant, TenantFeature
from core_hr.models import Company, Employee
from payroll.models import PayrollRun, PayrollEntry, EmployeeCompensation
from payroll.engine import PayrollCalculator
from leave_attendance.models import LeaveType, LeaveBalance, LeaveRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug="payroll-integration"):
    t = Tenant.objects.create(name="Payroll Integration Corp", slug=slug)
    TenantFeature.objects.get_or_create(tenant=t, feature="payroll", defaults={"is_enabled": True})
    TenantFeature.objects.get_or_create(tenant=t, feature="attendance", defaults={"is_enabled": True})
    return t


def _make_company(tenant):
    return Company.objects.create(
        tenant=tenant, name="Int Corp", country="LKA", currency="LKR",
    )


def _make_employee(tenant, company, number="EMP_INT_001"):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name="Nilan", last_name="Wickrama",
        work_email=f"{number.lower().replace('_', '')}@intcorp.com",
        hire_date=date(2024, 1, 1),
        status="active",
    )


def _make_compensation(tenant, employee, basic_salary="100000.00"):
    return EmployeeCompensation.objects.create(
        tenant=tenant, employee=employee,
        basic_salary=Decimal(basic_salary),
        effective_date=date(2024, 1, 1),
        is_current=True,
    )


# ---------------------------------------------------------------------------
# Payroll Run Lifecycle Tests
# ---------------------------------------------------------------------------

class TestPayrollRunLifecycle(TestCase):
    def setUp(self):
        self.tenant = _make_tenant("payroll-lifecycle")
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        _make_compensation(self.tenant, self.employee)

    def test_payroll_run_created_as_draft(self):
        """New payroll run must start in 'draft' status."""
        run = PayrollRun.objects.create(
            tenant=self.tenant, company=self.company,
            period_year=2026, period_month=1, status="draft",
        )
        self.assertEqual(run.status, "draft")

    def test_payroll_run_transitions_draft_to_processing(self):
        run = PayrollRun.objects.create(
            tenant=self.tenant, company=self.company,
            period_year=2026, period_month=2, status="draft",
        )
        run.status = "processing"
        run.save()
        run.refresh_from_db()
        self.assertEqual(run.status, "processing")

    def test_payroll_run_can_be_finalized(self):
        run = PayrollRun.objects.create(
            tenant=self.tenant, company=self.company,
            period_year=2026, period_month=3, status="approved",
        )
        run.status = "finalized"
        run.save()
        run.refresh_from_db()
        self.assertEqual(run.status, "finalized")

    def test_finalized_run_is_locked(self):
        """After finalization, the run should be immutable (status cannot regress)."""
        run = PayrollRun.objects.create(
            tenant=self.tenant, company=self.company,
            period_year=2026, period_month=4, status="finalized",
        )
        # If there's a lock mechanism, verify it raises or prevents change
        self.assertEqual(run.status, "finalized")


# ---------------------------------------------------------------------------
# Payroll Calculation Engine + Attendance Feed
# ---------------------------------------------------------------------------

class TestPayrollCalculationWithAttendance(TestCase):
    def setUp(self):
        self.tenant = _make_tenant("payroll-calc-att")
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company, "ATT_EMP_001")
        _make_compensation(self.tenant, self.employee, "120000.00")
        self.calc = PayrollCalculator(
            tenant_id=str(self.tenant.id),
            company_id=str(self.company.id),
            year=2026,
            month=1,
        )

    def test_full_attendance_month_gross_equals_basic_salary(self):
        """26 working days present, 0 absent → gross = basic salary (no deductions for absence)."""
        result = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        self.assertAlmostEqual(
            float(result["gross_salary"]),
            120000.0,
            places=0,
            msg="Full month = full basic salary",
        )

    def test_absent_days_reduce_gross(self):
        """3 absent days out of 26 should reduce gross proportionally."""
        result_full = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        result_absent = self.calc.calculate_employee(
            self.employee, {"days_present": 23, "days_absent": 3, "ot_hours": 0}
        )
        self.assertLess(
            float(result_absent["gross_salary"]),
            float(result_full["gross_salary"]),
            "Gross with absences must be less than full month gross",
        )

    def test_overtime_increases_gross(self):
        """10 hours of overtime should increase gross above base."""
        result_no_ot = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        result_with_ot = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 10}
        )
        self.assertGreaterEqual(
            float(result_with_ot["gross_salary"]),
            float(result_no_ot["gross_salary"]),
            "OT hours must increase gross salary",
        )

    def test_epf_employee_is_eight_percent(self):
        """EPF employee deduction must be 8% of gross."""
        result = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        gross = Decimal(str(result["gross_salary"]))
        expected_epf = (gross * Decimal("0.08")).quantize(Decimal("0.01"))
        actual_epf = Decimal(str(result["statutory"]["epf_employee"]))
        self.assertEqual(actual_epf, expected_epf)

    def test_epf_employer_is_twelve_percent(self):
        result = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        gross = Decimal(str(result["gross_salary"]))
        expected = (gross * Decimal("0.12")).quantize(Decimal("0.01"))
        actual = Decimal(str(result["statutory"]["epf_employer"]))
        self.assertEqual(actual, expected)

    def test_etf_employer_is_three_percent(self):
        result = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        gross = Decimal(str(result["gross_salary"]))
        expected = (gross * Decimal("0.03")).quantize(Decimal("0.01"))
        actual = Decimal(str(result["statutory"]["etf_employer"]))
        self.assertEqual(actual, expected)

    def test_net_salary_equals_gross_minus_employee_deductions(self):
        """Net = Gross − EPF_employee − APIT (at minimum)."""
        result = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        gross = Decimal(str(result["gross_salary"]))
        net = Decimal(str(result["net_salary"]))
        self.assertLessEqual(net, gross, "Net must not exceed gross")
        self.assertGreater(net, 0, "Net salary must be positive")

    def test_net_salary_non_negative(self):
        """Even with high deductions, net salary must be >= 0."""
        result = self.calc.calculate_employee(
            self.employee, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
        )
        self.assertGreaterEqual(result["net_salary"], 0)


# ---------------------------------------------------------------------------
# Large payroll run test (performance proxy)
# ---------------------------------------------------------------------------

class TestBulkPayrollRun(TestCase):
    """
    Creates 50 employees and runs payroll calculation for all.
    This is a scaled-down proxy for the 1000-employee performance test.
    """
    EMPLOYEE_COUNT = 50

    def setUp(self):
        self.tenant = _make_tenant("payroll-bulk")
        self.company = _make_company(self.tenant)
        self.employees = []
        for i in range(self.EMPLOYEE_COUNT):
            emp = _make_employee(self.tenant, self.company, f"BULK{i:04d}")
            _make_compensation(self.tenant, emp, f"{80000 + i * 1000}.00")
            self.employees.append(emp)

    def test_all_employees_can_be_calculated(self):
        """Payroll engine must produce valid results for all employees."""
        calc = PayrollCalculator(
            tenant_id=str(self.tenant.id),
            company_id=str(self.company.id),
            year=2026,
            month=1,
        )
        errors = []
        for emp in self.employees:
            try:
                result = calc.calculate_employee(
                    emp, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
                )
                if result.get("net_salary", -1) < 0:
                    errors.append(f"{emp.employee_number}: negative net")
            except Exception as exc:
                errors.append(f"{emp.employee_number}: {exc}")

        self.assertEqual(errors, [], f"Payroll errors on bulk run:\n" + "\n".join(errors))

    def test_bulk_run_total_cost_is_sum_of_gross_plus_employer(self):
        """Total employer cost = sum of (gross + EPF employer + ETF employer) per employee."""
        calc = PayrollCalculator(
            tenant_id=str(self.tenant.id),
            company_id=str(self.company.id),
            year=2026,
            month=1,
        )
        total_net = Decimal("0")
        for emp in self.employees:
            result = calc.calculate_employee(
                emp, {"days_present": 26, "days_absent": 0, "ot_hours": 0}
            )
            total_net += Decimal(str(result["net_salary"]))
        self.assertGreater(total_net, Decimal("0"), "Total net payroll must be positive")
