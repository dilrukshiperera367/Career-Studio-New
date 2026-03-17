"""
RLS (Row-Level Security) isolation tests.
Verifies that data from Tenant A is completely invisible to Tenant B
at both the Django ORM level and (where applicable) through the API.
"""

import pytest
from django.test import TestCase

from tenants.models import Tenant
from core_hr.models import Company, Department, Employee, Position
from leave_attendance.models import LeaveType, LeaveBalance, LeaveRequest
from payroll.models import PayrollRun, EmployeeCompensation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug):
    return Tenant.objects.create(name=slug.replace("-", " ").title(), slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name=f"{tenant.name} Co", country="LKA", currency="LKR")


def _make_employee(tenant, company, number="EMP001"):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name="Test", last_name="User",
        work_email=f"{number}@{tenant.slug}.com",
        hire_date="2024-01-01", status="active",
    )


# ---------------------------------------------------------------------------
# ORM-level isolation tests
# ---------------------------------------------------------------------------

class TestTenantIsolation(TestCase):
    """
    Ensure that filtering by tenant_id correctly isolates data at ORM level.
    These tests simulate what Django's queryset filter provides before RLS
    kicks in at the DB level.
    """

    def setUp(self):
        self.tenant_a = _make_tenant("tenant-a-rls")
        self.tenant_b = _make_tenant("tenant-b-rls")
        self.company_a = _make_company(self.tenant_a)
        self.company_b = _make_company(self.tenant_b)
        self.employee_a = _make_employee(self.tenant_a, self.company_a, "A001")
        self.employee_b = _make_employee(self.tenant_b, self.company_b, "B001")

    # -- Employees ------------------------------------------------------------

    def test_tenant_a_cannot_see_tenant_b_employees(self):
        """Filtering employees by tenant A must exclude tenant B records."""
        employees_a = Employee.objects.filter(tenant=self.tenant_a)
        pks_a = set(employees_a.values_list("pk", flat=True))
        self.assertIn(self.employee_a.pk, pks_a)
        self.assertNotIn(self.employee_b.pk, pks_a)

    def test_tenant_b_cannot_see_tenant_a_employees(self):
        employees_b = Employee.objects.filter(tenant=self.tenant_b)
        pks_b = set(employees_b.values_list("pk", flat=True))
        self.assertIn(self.employee_b.pk, pks_b)
        self.assertNotIn(self.employee_a.pk, pks_b)

    def test_tenant_a_employee_count_reflects_only_own_records(self):
        """Count should equal only tenant A's employees."""
        count = Employee.objects.filter(tenant=self.tenant_a).count()
        self.assertEqual(count, 1)

    # -- Companies / Departments ----------------------------------------------

    def test_company_scoped_to_tenant(self):
        companies_a = Company.objects.filter(tenant=self.tenant_a)
        self.assertEqual(companies_a.count(), 1)
        self.assertEqual(companies_a.first().tenant_id, self.tenant_a.id)

    def test_department_scoped_to_tenant(self):
        dept_a = Department.objects.create(
            tenant=self.tenant_a, company=self.company_a, name="Engineering"
        )
        Department.objects.create(
            tenant=self.tenant_b, company=self.company_b, name="Engineering"
        )
        depts_a = Department.objects.filter(tenant=self.tenant_a)
        self.assertEqual(depts_a.count(), 1)
        self.assertEqual(depts_a.first().pk, dept_a.pk)

    # -- Leave data -----------------------------------------------------------

    def test_leave_type_isolated_by_tenant(self):
        lt_a = LeaveType.objects.create(tenant=self.tenant_a, name="Annual", code="AL")
        lt_b = LeaveType.objects.create(tenant=self.tenant_b, name="Annual", code="AL")
        result = LeaveType.objects.filter(tenant=self.tenant_a)
        self.assertIn(lt_a, result)
        self.assertNotIn(lt_b, result)

    def test_leave_request_isolated_by_tenant(self):
        lt_a = LeaveType.objects.create(
            tenant=self.tenant_a, name="Annual", code="AL", max_days_per_year=14
        )
        lt_b = LeaveType.objects.create(
            tenant=self.tenant_b, name="Annual", code="AL", max_days_per_year=14
        )
        from decimal import Decimal
        from datetime import date, timedelta

        req_a = LeaveRequest.objects.create(
            tenant=self.tenant_a, employee=self.employee_a, leave_type=lt_a,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            days=Decimal("2"),
        )
        req_b = LeaveRequest.objects.create(
            tenant=self.tenant_b, employee=self.employee_b, leave_type=lt_b,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            days=Decimal("2"),
        )

        requests_a = LeaveRequest.objects.filter(tenant=self.tenant_a)
        pks_a = set(requests_a.values_list("pk", flat=True))
        self.assertIn(req_a.pk, pks_a)
        self.assertNotIn(req_b.pk, pks_a)

    # -- Payroll data ---------------------------------------------------------

    def test_payroll_run_isolated_by_tenant(self):
        run_a = PayrollRun.objects.create(
            tenant=self.tenant_a, company=self.company_a,
            period_year=2026, period_month=1, status="draft",
        )
        run_b = PayrollRun.objects.create(
            tenant=self.tenant_b, company=self.company_b,
            period_year=2026, period_month=1, status="draft",
        )
        runs_a = PayrollRun.objects.filter(tenant=self.tenant_a)
        self.assertIn(run_a, runs_a)
        self.assertNotIn(run_b, runs_a)


# ---------------------------------------------------------------------------
# Cross-tenant lookup prevention
# ---------------------------------------------------------------------------

class TestCrossTenantLookupPrevention(TestCase):
    """Attempt to fetch objects by PK but with wrong tenant — must return empty."""

    def setUp(self):
        self.tenant_a = _make_tenant("cross-a")
        self.tenant_b = _make_tenant("cross-b")
        self.company_a = _make_company(self.tenant_a)
        self.company_b = _make_company(self.tenant_b)
        self.employee_b = _make_employee(self.tenant_b, self.company_b, "B-CROSS")

    def test_fetching_tenant_b_employee_with_tenant_a_filter_returns_none(self):
        """Tenant A cannot retrieve Tenant B's employee by primary key."""
        result = Employee.objects.filter(
            pk=self.employee_b.pk,
            tenant=self.tenant_a,    # wrong tenant — must return nothing
        ).first()
        self.assertIsNone(result, "Cross-tenant PK lookup must return None")

    def test_bulk_queryset_does_not_leak(self):
        """All-employee queryset scoped to Tenant A must not include Tenant B records."""
        _make_employee(self.tenant_a, self.company_a, "A-CROSS")
        all_from_a = Employee.objects.filter(tenant=self.tenant_a)
        all_pks = set(all_from_a.values_list("pk", flat=True))
        self.assertNotIn(self.employee_b.pk, all_pks)
