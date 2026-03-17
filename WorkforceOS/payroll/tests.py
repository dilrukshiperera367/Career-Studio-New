"""
Payroll tests — engine calculations (EPF/ETF/APIT), payroll run lifecycle,
final settlement, and gratuity logic.
"""

from decimal import Decimal
from django.test import TestCase

from tenants.models import Tenant
from core_hr.models import Company, Employee
from payroll.models import PayrollRun, PayrollEntry, EmployeeCompensation
from payroll.engine import PayrollCalculator
from payroll.advanced import calculate_gratuity, calculate_final_settlement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='payroll-test'):
    return Tenant.objects.create(name='Payroll Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(
        tenant=tenant, name='Payroll Test Co.',
        country='LKA', currency='LKR',
    )


def _make_employee(tenant, company, *, number='EMP001', hire_date='2020-01-01'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Sam', last_name='Silva',
        work_email=f'{number.lower()}@example.com',
        hire_date=hire_date, status='active',
    )


def _make_compensation(tenant, employee, basic_salary):
    return EmployeeCompensation.objects.create(
        tenant=tenant, employee=employee,
        basic_salary=basic_salary,
        effective_date='2024-01-01', is_current=True,
    )


def _calc(tenant, company):
    return PayrollCalculator(
        tenant_id=str(tenant.id),
        company_id=str(company.id),
        year=2024, month=1,
    )


# ---------------------------------------------------------------------------
# EPF / ETF statutory rate tests
# ---------------------------------------------------------------------------

class TestPayrollEngineStatutory(TestCase):
    """Verify EPF/ETF/APIT defaults when no StatutoryRule records exist."""

    def setUp(self):
        self.tenant = _make_tenant('statutory-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        _make_compensation(self.tenant, self.employee, Decimal('100000.00'))
        self.calc = _calc(self.tenant, self.company)

    def test_epf_employee_is_eight_percent(self):
        """EPF employee contribution must be 8% of gross."""
        result = self.calc.calculate_employee(self.employee, {'days_present': 26, 'days_absent': 0})
        gross = Decimal(str(result['gross_salary']))
        expected = (gross * Decimal('0.08')).quantize(Decimal('0.01'))
        actual = Decimal(str(result['statutory']['epf_employee']))
        self.assertEqual(actual, expected)

    def test_epf_employer_is_twelve_percent(self):
        """EPF employer contribution must be 12% of gross."""
        result = self.calc.calculate_employee(self.employee, {'days_present': 26, 'days_absent': 0})
        gross = Decimal(str(result['gross_salary']))
        expected = (gross * Decimal('0.12')).quantize(Decimal('0.01'))
        actual = Decimal(str(result['statutory']['epf_employer']))
        self.assertEqual(actual, expected)

    def test_etf_employer_is_three_percent(self):
        """ETF employer contribution must be 3% of gross."""
        result = self.calc.calculate_employee(self.employee, {'days_present': 26, 'days_absent': 0})
        gross = Decimal(str(result['gross_salary']))
        expected = (gross * Decimal('0.03')).quantize(Decimal('0.01'))
        actual = Decimal(str(result['statutory']['etf_employer']))
        self.assertEqual(actual, expected)

    def test_net_salary_leq_gross(self):
        """Net salary cannot exceed gross salary."""
        result = self.calc.calculate_employee(self.employee, {'days_present': 26, 'days_absent': 0})
        self.assertLessEqual(result['net_salary'], result['gross_salary'])

    def test_net_salary_non_negative(self):
        """Net salary must be >= 0."""
        result = self.calc.calculate_employee(self.employee, {'days_present': 26, 'days_absent': 0})
        self.assertGreaterEqual(result['net_salary'], 0)

    def test_employer_total_cost_formula(self):
        """employer_total_cost == gross + EPF_employer + ETF_employer."""
        result = self.calc.calculate_employee(self.employee, {'days_present': 26, 'days_absent': 0})
        expected = (
            Decimal(str(result['gross_salary']))
            + Decimal(str(result['statutory']['epf_employer']))
            + Decimal(str(result['statutory']['etf_employer']))
        )
        actual = Decimal(str(result['employer_total_cost']))
        self.assertAlmostEqual(float(actual), float(expected), places=1)

    def test_result_contains_required_keys(self):
        """Calculation result must include all documented keys."""
        result = self.calc.calculate_employee(self.employee, None)
        for key in [
            'basic_salary', 'earnings', 'deductions', 'statutory',
            'gross_salary', 'net_salary', 'employer_total_cost',
            'days_worked', 'days_absent',
        ]:
            self.assertIn(key, result, f"Missing key: {key}")


# ---------------------------------------------------------------------------
# APIT slab tests
# ---------------------------------------------------------------------------

class TestAPIT(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('apit-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.calc = _calc(self.tenant, self.company)

    def test_at_threshold_zero_apit(self):
        """Annual income == LKR 1,200,000 (monthly 100,000) → APIT == 0."""
        _make_compensation(self.tenant, self.employee, Decimal('100000.00'))
        result = self.calc.calculate_employee(self.employee, None)
        self.assertEqual(result['statutory']['apit'], 0.0)

    def test_above_threshold_positive_apit(self):
        """Monthly income > LKR 141,667 (annual > 1,700,000) triggers APIT."""
        _make_compensation(self.tenant, self.employee, Decimal('200000.00'))
        result = self.calc.calculate_employee(self.employee, None)
        self.assertGreater(result['statutory']['apit'], 0)

    def test_higher_income_higher_apit(self):
        """Higher gross salary results in strictly higher APIT."""
        _make_compensation(self.tenant, self.employee, Decimal('200000.00'))
        result_low = self.calc.calculate_employee(self.employee, None)
        self.employee.compensations.filter(is_current=True).update(
            basic_salary=Decimal('500000.00')
        )
        result_high = self.calc.calculate_employee(self.employee, None)
        self.assertGreater(result_high['statutory']['apit'], result_low['statutory']['apit'])


# ---------------------------------------------------------------------------
# Absent day deduction tests
# ---------------------------------------------------------------------------

class TestAbsentDeductions(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('absent-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        _make_compensation(self.tenant, self.employee, Decimal('90000.00'))
        self.calc = _calc(self.tenant, self.company)

    def test_absent_days_reduce_net(self):
        """Net salary with absences must be less than full-attendance net."""
        full = self.calc.calculate_employee(self.employee, {'days_present': 26, 'days_absent': 0})
        with_absence = self.calc.calculate_employee(self.employee, {'days_present': 22, 'days_absent': 4})
        self.assertLess(with_absence['net_salary'], full['net_salary'])

    def test_days_absent_reflected_in_result(self):
        """days_absent in result must match attendance_data input."""
        result = self.calc.calculate_employee(self.employee, {'days_present': 22, 'days_absent': 4})
        self.assertEqual(result['days_absent'], 4)


# ---------------------------------------------------------------------------
# OT calculation tests
# ---------------------------------------------------------------------------

class TestOvertimeCalculation(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('ot-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        _make_compensation(self.tenant, self.employee, Decimal('60000.00'))
        self.calc = _calc(self.tenant, self.company)

    def test_ot_amount_positive_when_ot_hours_given(self):
        """OT hours > 0 should result in ot_amount > 0."""
        result = self.calc.calculate_employee(
            self.employee, {'days_present': 26, 'days_absent': 0, 'ot_hours': 10}
        )
        self.assertGreater(result.get('ot_amount', 0), 0)

    def test_ot_formula(self):
        """OT amount = (basic / 240) * 1.5 * ot_hours."""
        result = self.calc.calculate_employee(
            self.employee, {'days_present': 26, 'days_absent': 0, 'ot_hours': 8}
        )
        basic = Decimal('60000.00')
        expected_ot = float((basic / Decimal('240')) * Decimal('1.5') * Decimal('8'))
        self.assertAlmostEqual(result.get('ot_amount', 0), expected_ot, places=1)


# ---------------------------------------------------------------------------
# Gratuity tests
# ---------------------------------------------------------------------------

class TestGratuityCalculation(TestCase):
    def test_below_five_years_no_gratuity(self):
        """Employees with < 5 years service get 0 gratuity."""
        result = calculate_gratuity(Decimal('80000.00'), 4, 'LKA')
        self.assertEqual(result, Decimal('0'))

    def test_five_years_gratuity_formula(self):
        """Gratuity = 0.5 * monthly_basic * years_of_service (LKA, >=5 yrs)."""
        basic = Decimal('100000.00')
        years = 10
        result = calculate_gratuity(basic, years, 'LKA')
        expected = basic / 2 * years
        self.assertAlmostEqual(float(result), float(expected), places=1)

    def test_gratuity_non_negative(self):
        """Gratuity is always >= 0."""
        result = calculate_gratuity(Decimal('50000.00'), 7, 'LKA')
        self.assertGreaterEqual(result, Decimal('0'))


# ---------------------------------------------------------------------------
# Final settlement tests
# ---------------------------------------------------------------------------

class TestFinalSettlement(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('settlement-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company, hire_date='2015-01-01')
        self.compensation = _make_compensation(
            self.tenant, self.employee, Decimal('120000.00')
        )

    def test_settlement_has_required_keys(self):
        """Final settlement result must contain gross_settlement and net_settlement."""
        from datetime import date
        result = calculate_final_settlement(
            employee_compensation=self.compensation,
            employee=self.employee,
            leave_balances=[],
            pending_loans=[],
            last_working_date=date(2025, 1, 31),
        )
        self.assertIn('gross_settlement', result)
        self.assertIn('net_settlement', result)
        self.assertIn('components', result)

    def test_net_leq_gross_settlement(self):
        """Net settlement must be <= gross settlement."""
        from datetime import date
        result = calculate_final_settlement(
            employee_compensation=self.compensation,
            employee=self.employee,
            leave_balances=[],
            pending_loans=[],
            last_working_date=date(2025, 1, 31),
        )
        self.assertLessEqual(result['net_settlement'], result['gross_settlement'])


# ---------------------------------------------------------------------------
# PayrollRun model constraint tests
# ---------------------------------------------------------------------------

class TestPayrollRunConstraints(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('run-test')
        self.company = _make_company(self.tenant)

    def test_unique_per_period(self):
        """Two payroll runs for same tenant/company/year/month disallowed."""
        PayrollRun.objects.create(
            tenant=self.tenant, company=self.company,
            period_year=2024, period_month=1,
        )
        with self.assertRaises(Exception):
            PayrollRun.objects.create(
                tenant=self.tenant, company=self.company,
                period_year=2024, period_month=1,
            )

    def test_default_status_is_draft(self):
        """PayrollRun starts in 'draft' status."""
        run = PayrollRun.objects.create(
            tenant=self.tenant, company=self.company,
            period_year=2024, period_month=2,
        )
        self.assertEqual(run.status, 'draft')
