"""
Payroll engine — core business logic for calculating payroll.
Statutory rules (EPF/ETF/APIT) for Sri Lanka.
"""

import logging
from decimal import Decimal
from datetime import date
from .models import EmployeeCompensation, StatutoryRule, PayrollEntry, LoanRecord

logger = logging.getLogger('hrm')


class PayrollCalculator:
    """
    Calculates payroll for a single employee for a given month.
    Sri Lanka statutory compliance: EPF 8%/12%, ETF 3%, APIT.
    """

    def __init__(self, tenant_id, company_id, year, month):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.year = year
        self.month = month
        self.statutory_rules = self._load_statutory_rules()

    def _load_statutory_rules(self):
        """Load active statutory rules for the relevant country."""
        rules = {}
        for rule in StatutoryRule.objects.filter(
            country='LKA',
            is_active=True,
            effective_from__lte=date(self.year, self.month, 1)
        ).order_by('-effective_from'):
            if rule.rule_type not in rules:
                rules[rule.rule_type] = rule
        return rules

    def calculate_employee(self, employee, attendance_data=None):
        """Calculate payroll for a single employee."""
        # Get current compensation
        compensation = EmployeeCompensation.objects.filter(
            tenant_id=self.tenant_id,
            employee=employee,
            is_current=True,
        ).first()

        if not compensation:
            logger.warning(f"No compensation found for {employee}")
            return None

        basic = compensation.basic_salary
        result = {
            'basic_salary': basic,
            'earnings': [],
            'deductions': [],
            'statutory': {},
        }

        # --- Earnings ---
        total_earnings = basic

        # Process salary structure components
        if compensation.salary_structure and compensation.salary_structure.components:
            for comp in compensation.salary_structure.components:
                if comp.get('type') == 'earning':
                    amount = self._calc_component(comp, basic, total_earnings)
                    result['earnings'].append({
                        'component': comp['name'],
                        'amount': float(amount),
                    })
                    total_earnings += amount

        # OT pay
        ot_hours = Decimal(str(attendance_data.get('ot_hours', 0))) if attendance_data else Decimal('0')
        ot_rate = basic / Decimal('240')  # Hourly rate = basic / (30 days * 8 hours)
        ot_amount = ot_hours * ot_rate * Decimal('1.5')
        result['ot_hours'] = float(ot_hours)
        result['ot_amount'] = float(ot_amount)
        total_earnings += ot_amount

        result['total_earnings'] = float(total_earnings)
        result['gross_salary'] = float(total_earnings)

        # --- Deductions ---
        total_deductions = Decimal('0')

        # Process deduction components from salary structure
        if compensation.salary_structure and compensation.salary_structure.components:
            for comp in compensation.salary_structure.components:
                if comp.get('type') == 'deduction':
                    amount = self._calc_component(comp, basic, total_earnings)
                    result['deductions'].append({
                        'component': comp['name'],
                        'amount': float(amount),
                    })
                    total_deductions += amount

        # Absent day deduction
        days_absent = attendance_data.get('days_absent', 0) if attendance_data else 0
        if days_absent > 0:
            daily_rate = basic / Decimal('30')
            absent_deduction = daily_rate * Decimal(str(days_absent))
            result['deductions'].append({
                'component': 'Absent Day Deduction',
                'amount': float(absent_deduction),
            })
            total_deductions += absent_deduction

        # --- Statutory Calculations (Sri Lanka) ---
        # EPF Employee: 8% of total earnings
        epf_employee = self._calc_statutory('epf_employee', total_earnings)
        result['statutory']['epf_employee'] = float(epf_employee)
        total_deductions += epf_employee

        # APIT (Advanced Personal Income Tax)
        apit = self._calc_apit(total_earnings)
        result['statutory']['apit'] = float(apit)
        total_deductions += apit

        # EPF Employer: 12% (not deducted from employee pay)
        epf_employer = self._calc_statutory('epf_employer', total_earnings)
        result['statutory']['epf_employer'] = float(epf_employer)

        # ETF Employer: 3% (not deducted from employee pay)
        etf_employer = self._calc_statutory('etf', total_earnings)
        result['statutory']['etf_employer'] = float(etf_employer)

        # --- Loan deductions ---
        loan_deductions = []
        active_loans = LoanRecord.objects.filter(
            tenant_id=self.tenant_id,
            employee=employee,
            status='active',
        )
        for loan in active_loans:
            amount = min(loan.installment_amount, loan.outstanding_balance)
            loan_deductions.append({
                'loan_id': str(loan.id),
                'amount': float(amount),
                'remaining': float(loan.outstanding_balance - amount),
            })
            total_deductions += amount

        result['loan_deductions'] = loan_deductions
        result['total_deductions'] = float(total_deductions)

        # --- Net ---
        net = total_earnings - total_deductions
        result['net_salary'] = float(net)

        # --- Employer total cost ---
        result['employer_total_cost'] = float(total_earnings + epf_employer + etf_employer)

        # Attendance data
        result['days_worked'] = attendance_data.get('days_present', 0) if attendance_data else 0
        result['days_absent'] = days_absent

        return result

    def _calc_component(self, component, basic, gross):
        """Calculate a salary component."""
        calc_type = component.get('calc_type', 'fixed')
        value = Decimal(str(component.get('value', 0)))

        if calc_type == 'fixed':
            return value
        elif calc_type == 'percentage':
            basis = basic if component.get('basis') == 'basic' else gross
            return (basis * value / Decimal('100')).quantize(Decimal('0.01'))
        return Decimal('0')

    def _calc_statutory(self, rule_type, amount):
        """Calculate statutory contribution using loaded rules."""
        rule = self.statutory_rules.get(rule_type)
        if not rule:
            # Default rates if no rule found
            defaults = {
                'epf_employee': Decimal('0.08'),
                'epf_employer': Decimal('0.12'),
                'etf': Decimal('0.03'),
            }
            rate = defaults.get(rule_type, Decimal('0'))
            return (amount * rate).quantize(Decimal('0.01'))

        calc = rule.calculation
        if calc.get('type') == 'percentage':
            return (amount * Decimal(str(calc['rate']))).quantize(Decimal('0.01'))
        return Decimal('0')

    def _calc_apit(self, monthly_gross):
        """
        Calculate APIT (Advanced Personal Income Tax) for Sri Lanka.
        Uses annual projection method with tax slabs.
        """
        rule = self.statutory_rules.get('income_tax')
        if not rule:
            # Default 2024 Sri Lanka APIT slabs
            slabs = [
                {'from': 0, 'to': 1200000, 'rate': 0},
                {'from': 1200000, 'to': 1700000, 'rate': 6},
                {'from': 1700000, 'to': 2200000, 'rate': 12},
                {'from': 2200000, 'to': 2700000, 'rate': 18},
                {'from': 2700000, 'to': 3200000, 'rate': 24},
                {'from': 3200000, 'to': 3700000, 'rate': 30},
                {'from': 3700000, 'to': None, 'rate': 36},
            ]
        else:
            slabs = rule.calculation.get('slabs', [])

        # Project annual income
        annual_gross = monthly_gross * 12
        annual_tax = Decimal('0')

        for slab in slabs:
            slab_from = Decimal(str(slab['from']))
            slab_to = Decimal(str(slab['to'])) if slab.get('to') else Decimal('999999999')
            rate = Decimal(str(slab['rate'])) / Decimal('100')

            if annual_gross <= slab_from:
                break

            taxable_in_slab = min(annual_gross, slab_to) - slab_from
            if taxable_in_slab > 0:
                annual_tax += (taxable_in_slab * rate).quantize(Decimal('0.01'))

        # Monthly APIT = annual tax / 12
        monthly_apit = (annual_tax / 12).quantize(Decimal('0.01'))
        return monthly_apit
