"""Unit tests for the payroll calculator engine."""
import pytest
from decimal import Decimal
from datetime import date


@pytest.mark.django_db
class TestPayrollCalculator:

    def test_calculate_zero_salary(self):
        from payroll.calculator import calculate_payroll

        class FakeEmployee:
            id = 1
            salary = 0
            basic_salary = 0
            hourly_rate = None
            gross_salary = None

        result = calculate_payroll(FakeEmployee(), date(2026, 3, 1), date(2026, 3, 31))
        assert result.gross_pay == Decimal('0')
        assert result.net_pay == Decimal('0')
        assert result.total_deductions == Decimal('0')

    def test_calculate_with_salary(self):
        from payroll.calculator import calculate_payroll

        class FakeEmployee:
            id = 2
            salary = None
            basic_salary = Decimal('60000')  # Annual salary
            hourly_rate = None
            gross_salary = None

        result = calculate_payroll(FakeEmployee(), date(2026, 3, 1), date(2026, 3, 31))
        # Should have positive gross
        assert result.gross_pay > 0
        # Net should be <= gross
        assert result.net_pay <= result.gross_pay

    def test_net_never_negative(self):
        from payroll.calculator import calculate_payroll, DeductionResult

        class FakeEmployee:
            id = 3
            salary = None
            basic_salary = Decimal('12000')  # Low salary
            hourly_rate = None
            gross_salary = None

        result = calculate_payroll(FakeEmployee(), date(2026, 3, 1), date(2026, 3, 31))
        assert result.net_pay >= Decimal('0')

    def test_deduction_result_dataclass(self):
        from payroll.calculator import DeductionResult
        d = DeductionResult(name='Test Tax', amount=Decimal('100'), is_statutory=True)
        assert d.name == 'Test Tax'
        assert d.amount == Decimal('100')
        assert d.is_statutory is True

    def test_payroll_calculation_properties(self):
        from payroll.calculator import PayrollCalculation, DeductionResult
        calc = PayrollCalculation(
            employee_id=1,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            gross_pay=Decimal('5000'),
        )
        calc.deductions = [
            DeductionResult('Tax', Decimal('400'), True),
            DeductionResult('EPF', Decimal('200'), True),
        ]
        assert calc.total_deductions == Decimal('600')
        assert calc.net_pay == Decimal('4400')
        assert calc.statutory_deductions == Decimal('600')
