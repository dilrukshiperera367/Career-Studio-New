"""
Payroll calculation engine.
Computes gross pay, statutory deductions (APIT income tax, EPF, ETF),
voluntary deductions (benefits, loans), and net pay.

Adapted for the HRM System model schema:
  - EmployeeCompensation.basic_salary  (Decimal, monthly)
  - EmployeeCompensation.gross_salary  (Decimal, optional pre-computed monthly gross)
  - PayrollRun.total_gross / .total_deductions / .total_net
  - PayrollEntry.gross_salary / .net_salary / .total_deductions
  - Sri Lanka statutory: EPF 8% (employee), EPF 12% (employer),
                         ETF 3% (employer), APIT (progressive income tax)
"""
from __future__ import annotations

import decimal
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

logger = logging.getLogger('hrm')

D = decimal.Decimal


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DeductionResult:
    name: str
    amount: D
    is_statutory: bool = False


@dataclass
class PayrollCalculation:
    employee_id: int
    period_start: date
    period_end: date
    gross_pay: D = D('0')
    deductions: List[DeductionResult] = field(default_factory=list)

    @property
    def total_deductions(self) -> D:
        return sum((d.amount for d in self.deductions), D('0'))

    @property
    def net_pay(self) -> D:
        return max(D('0'), self.gross_pay - self.total_deductions)

    @property
    def statutory_deductions(self) -> D:
        return sum((d.amount for d in self.deductions if d.is_statutory), D('0'))

    @property
    def epf_employee(self) -> D:
        for d in self.deductions:
            if d.name == 'EPF (Employee 8%)':
                return d.amount
        return D('0')

    @property
    def epf_employer(self) -> D:
        for d in self.deductions:
            if d.name == 'EPF (Employer 12%)':
                return d.amount
        return D('0')

    @property
    def etf_employer(self) -> D:
        for d in self.deductions:
            if d.name == 'ETF (Employer 3%)':
                return d.amount
        return D('0')

    @property
    def apit(self) -> D:
        for d in self.deductions:
            if d.name == 'APIT':
                return d.amount
        return D('0')


# ---------------------------------------------------------------------------
# Sri Lanka statutory calculations
# ---------------------------------------------------------------------------

def _apit(monthly_gross: D) -> D:
    """
    Advanced Personal Income Tax (APIT) — Sri Lanka progressive rates.
    Applied monthly based on annualised gross.
    Rates as per Inland Revenue Act (simplified 2024 schedule):
      Annual up to  3,000,000 LKR → 6%
      Up to  6,000,000 LKR        → 12%
      Up to  9,000,000 LKR        → 18%
      Up to 12,000,000 LKR        → 24%
      Above 12,000,000 LKR        → 36%
    First 1,200,000 LKR p.a. is exempt (tax-free threshold).
    """
    annual = monthly_gross * D('12')
    exempt = D('1200000')

    if annual <= exempt:
        return D('0')

    taxable = annual - exempt

    if taxable <= D('1800000'):          # 0–1.8M taxable → 6%
        annual_tax = taxable * D('0.06')
    elif taxable <= D('4800000'):        # 1.8M–4.8M → 12%
        annual_tax = D('1800000') * D('0.06') + (taxable - D('1800000')) * D('0.12')
    elif taxable <= D('7800000'):        # 4.8M–7.8M → 18%
        annual_tax = D('108000') + D('360000') + (taxable - D('4800000')) * D('0.18')
    elif taxable <= D('10800000'):       # 7.8M–10.8M → 24%
        annual_tax = D('108000') + D('360000') + D('540000') + (taxable - D('7800000')) * D('0.24')
    else:                                # above 10.8M → 36%
        annual_tax = D('108000') + D('360000') + D('540000') + D('720000') + (taxable - D('10800000')) * D('0.36')

    return (annual_tax / D('12')).quantize(D('0.01'), rounding=decimal.ROUND_HALF_UP)


def _epf_employee(gross: D, rate: D = D('0.08')) -> D:
    """EPF employee contribution — default 8% of gross earnings."""
    return (gross * rate).quantize(D('0.01'), rounding=decimal.ROUND_HALF_UP)


def _epf_employer(gross: D, rate: D = D('0.12')) -> D:
    """EPF employer contribution — default 12% of gross earnings."""
    return (gross * rate).quantize(D('0.01'), rounding=decimal.ROUND_HALF_UP)


def _etf_employer(gross: D, rate: D = D('0.03')) -> D:
    """ETF employer contribution — default 3% of gross earnings."""
    return (gross * rate).quantize(D('0.01'), rounding=decimal.ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_payroll(
    employee,
    period_start: date,
    period_end: date,
    extra_allowances: D = D('0'),
    voluntary_deductions: Optional[List[DeductionResult]] = None,
    compensation=None,
) -> PayrollCalculation:
    """
    Calculate payroll for a single employee for a given period.

    Args:
        employee: ``core_hr.Employee`` model instance.
        period_start / period_end: pay period boundary dates (inclusive).
        extra_allowances: bonuses, overtime pay, arrears, etc.
        voluntary_deductions: loan repayments, pension top-ups, etc.
        compensation: ``payroll.EmployeeCompensation`` instance (optional).
                      If omitted the latest active record is fetched automatically.

    Returns:
        PayrollCalculation with gross, per-deduction breakdown, and net pay.

    Model field mapping
    -------------------
    EmployeeCompensation.basic_salary  → base salary (monthly)
    EmployeeCompensation.gross_salary  → optional pre-computed monthly gross
    """
    # ------------------------------------------------------------------ #
    # 1. Resolve compensation record
    # ------------------------------------------------------------------ #
    if compensation is None:
        try:
            from payroll.models import EmployeeCompensation
            compensation = EmployeeCompensation.objects.filter(
                employee=employee,
                is_current=True,
            ).order_by('-effective_date').first()
        except Exception as exc:
            logger.warning("calculator: could not fetch compensation for %s: %s", employee, exc)
            compensation = None

    # ------------------------------------------------------------------ #
    # 2. Determine gross pay for the period
    # ------------------------------------------------------------------ #
    days_in_period = (period_end - period_start).days + 1

    if compensation is not None:
        # Use pre-computed gross if available, else basic salary
        monthly_gross = D(str(
            compensation.gross_salary or compensation.basic_salary or '0'
        ))
    else:
        monthly_gross = D('0')

        # Fallback: check for direct employee-level salary attributes
        for attr in ('salary', 'base_salary', 'basic_salary'):
            val = getattr(employee, attr, None)
            if val:
                monthly_gross = D(str(val))
                break

    # Pro-rate to period (assume 30-day month)
    gross = (monthly_gross / D('30') * D(str(days_in_period))).quantize(
        D('0.01'), rounding=decimal.ROUND_HALF_UP
    )
    gross += extra_allowances

    calc = PayrollCalculation(
        employee_id=employee.id,
        period_start=period_start,
        period_end=period_end,
        gross_pay=gross,
    )

    if gross <= D('0'):
        logger.debug("calculator: zero gross for employee %s — skipping statutory deductions", employee)
        if voluntary_deductions:
            calc.deductions.extend(voluntary_deductions)
        return calc

    # ------------------------------------------------------------------ #
    # 3. Statutory deductions (Sri Lanka)
    # ------------------------------------------------------------------ #
    apit_amount = _apit(monthly_gross)  # APIT is monthly-based, not pro-rated
    epf_emp_amount = _epf_employee(gross)
    epf_er_amount = _epf_employer(gross)
    etf_er_amount = _etf_employer(gross)

    # Only EPF employee contribution reduces employee net pay
    calc.deductions.append(DeductionResult(
        name='EPF (Employee 8%)', amount=epf_emp_amount, is_statutory=True
    ))
    calc.deductions.append(DeductionResult(
        name='EPF (Employer 12%)', amount=epf_er_amount, is_statutory=False  # employer cost, not employee deduction
    ))
    calc.deductions.append(DeductionResult(
        name='ETF (Employer 3%)', amount=etf_er_amount, is_statutory=False   # employer cost
    ))
    if apit_amount > D('0'):
        calc.deductions.append(DeductionResult(
            name='APIT', amount=apit_amount, is_statutory=True
        ))

    # ------------------------------------------------------------------ #
    # 4. Voluntary deductions
    # ------------------------------------------------------------------ #
    if voluntary_deductions:
        calc.deductions.extend(voluntary_deductions)

    return calc


def apply_calculation_to_run(payroll_run, calculation: PayrollCalculation) -> None:
    """
    Persist aggregate totals from a ``PayrollCalculation`` back to a
    ``PayrollRun`` (or any object with matching total fields).

    ``PayrollRun`` field mapping:
        total_gross        ← calculation.gross_pay
        total_net          ← calculation.net_pay
        total_deductions   ← calculation.total_deductions (employee-side only)
    """
    updated = False

    # gross
    for fname in ('total_gross', 'gross_amount', 'gross_pay'):
        if hasattr(payroll_run, fname):
            setattr(payroll_run, fname, calculation.gross_pay)
            updated = True
            break

    # net
    for fname in ('total_net', 'net_amount', 'net_pay', 'net_salary'):
        if hasattr(payroll_run, fname):
            setattr(payroll_run, fname, calculation.net_pay)
            updated = True
            break

    # deductions (employee-side only — statutory employee + voluntary)
    employee_deductions = sum(
        (d.amount for d in calculation.deductions
         if d.name in ('EPF (Employee 8%)', 'APIT') or not d.name.startswith('EPF (Employer') and not d.name.startswith('ETF')),
        D('0'),
    )
    for fname in ('total_deductions', 'deductions_amount', 'total_deduction'):
        if hasattr(payroll_run, fname):
            setattr(payroll_run, fname, employee_deductions)
            updated = True
            break

    if updated:
        try:
            payroll_run.save()
        except Exception as exc:
            logger.error("apply_calculation_to_run: save failed for %s: %s", payroll_run, exc)
