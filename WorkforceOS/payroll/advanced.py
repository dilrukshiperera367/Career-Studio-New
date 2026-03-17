"""
Payroll Advanced — Gratuity calculation, final settlement, arrears processing.
Sri Lanka compliance: Gratuity Act (Payment of Gratuity Act No. 12 of 1983).
"""

from decimal import Decimal
from datetime import date


def calculate_gratuity(basic_salary, years_of_service, country='LKA'):
    """
    Calculate gratuity based on country rules.

    Sri Lanka (LKA):
        - Eligible after 5 years of continuous service
        - Half month's salary for each year of service
        - Based on last drawn basic salary

    Args:
        basic_salary: Decimal — last drawn basic salary
        years_of_service: Decimal — total years of service (can be fractional)
        country: country code

    Returns:
        dict with gratuity_amount, eligible, formula
    """
    basic = Decimal(str(basic_salary))
    years = Decimal(str(years_of_service))

    if country == 'LKA':
        eligible = years >= 5
        if not eligible:
            return {
                'gratuity_amount': Decimal('0'),
                'eligible': False,
                'formula': 'Not eligible (min 5 years required)',
                'years_of_service': float(years),
            }

        # Half month salary per year of service
        gratuity = (basic / 2) * years
        return {
            'gratuity_amount': gratuity.quantize(Decimal('0.01')),
            'eligible': True,
            'formula': f'({basic} / 2) × {years} years = {gratuity.quantize(Decimal("0.01"))}',
            'years_of_service': float(years),
        }

    return {'gratuity_amount': Decimal('0'), 'eligible': False, 'formula': 'Country not supported'}


def calculate_final_settlement(employee_compensation, employee, leave_balances=None,
                                pending_loans=None, last_working_date=None):
    """
    Calculate final settlement for an exiting employee.

    Components:
        1. Remaining salary (pro-rata for partial month)
        2. Leave encashment (unused leave × daily rate)
        3. Gratuity (if eligible)
        4. Pending loan deductions
        5. Any pending reimbursements
    """
    last_day = last_working_date or date.today()
    comp = employee_compensation

    basic = Decimal(str(comp.basic_salary))
    gross = Decimal(str(comp.gross_salary))
    daily_rate = gross / 30  # Approximate daily rate

    # 1. Pro-rata salary for remaining days in the month
    remaining_days = last_day.day
    prorata_salary = (gross / 30 * remaining_days).quantize(Decimal('0.01'))

    # 2. Leave encashment
    leave_encashment = Decimal('0')
    leave_details = []
    if leave_balances:
        for balance in leave_balances:
            if balance.remaining > 0 and hasattr(balance, 'leave_type') and balance.leave_type.paid:
                days = Decimal(str(balance.remaining))
                amount = (daily_rate * days).quantize(Decimal('0.01'))
                leave_encashment += amount
                leave_details.append({
                    'leave_type': balance.leave_type.name,
                    'days': float(days),
                    'amount': float(amount),
                })

    # 3. Gratuity
    hire_date = employee.hire_date
    if hire_date:
        service_days = (last_day - hire_date).days
        years_of_service = Decimal(str(service_days)) / Decimal('365.25')
    else:
        years_of_service = Decimal('0')

    gratuity_result = calculate_gratuity(basic, years_of_service)

    # 4. Loan deductions
    total_loan_outstanding = Decimal('0')
    if pending_loans:
        for loan in pending_loans:
            outstanding = Decimal(str(loan.outstanding_balance))
            total_loan_outstanding += outstanding

    # 5. Calculate total
    gross_settlement = prorata_salary + leave_encashment + gratuity_result['gratuity_amount']
    net_settlement = gross_settlement - total_loan_outstanding

    return {
        'employee_name': employee.full_name,
        'employee_number': employee.employee_number,
        'last_working_date': str(last_day),
        'years_of_service': float(years_of_service),
        'components': {
            'prorata_salary': float(prorata_salary),
            'leave_encashment': float(leave_encashment),
            'leave_details': leave_details,
            'gratuity': float(gratuity_result['gratuity_amount']),
            'gratuity_eligible': gratuity_result['eligible'],
            'gratuity_formula': gratuity_result['formula'],
            'loan_deductions': float(total_loan_outstanding),
        },
        'gross_settlement': float(gross_settlement),
        'net_settlement': float(net_settlement),
    }


def process_arrears(employee_id, old_salary, new_salary, effective_from, backdate_to, months=None):
    """
    Calculate salary arrears for backdated salary changes.

    When an employee gets a salary revision effective from a past date,
    this calculates the difference owed for each retroactive month.

    Args:
        employee_id: Employee UUID
        old_salary: Previous gross salary
        new_salary: New gross salary
        effective_from: Date the new salary should have started
        backdate_to: Date from which to calculate arrears
        months: Optional list of (year, month) tuples to calculate for

    Returns:
        dict with per-month arrears and total
    """
    old = Decimal(str(old_salary))
    new_sal = Decimal(str(new_salary))
    diff = new_sal - old

    if diff <= 0:
        return {'arrears': [], 'total_arrears': 0, 'message': 'No arrears (salary decreased or unchanged)'}

    from datetime import datetime
    if not months:
        months = []
        current = backdate_to
        while current <= effective_from:
            months.append((current.year, current.month))
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

    arrears = []
    total = Decimal('0')
    for year, month in months:
        amount = diff.quantize(Decimal('0.01'))
        total += amount
        arrears.append({
            'year': year,
            'month': month,
            'old_salary': float(old),
            'new_salary': float(new_sal),
            'difference': float(amount),
        })

    return {
        'employee_id': str(employee_id),
        'arrears': arrears,
        'total_arrears': float(total),
        'months_covered': len(arrears),
    }
