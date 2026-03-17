"""
Multi-Country Payroll — Configurable statutory rules engine with country plugins.
Supports: Sri Lanka (existing), India (PF/ESI/TDS/PT), UAE (WPS/gratuity/visa).
"""

from decimal import Decimal
from datetime import date


class StatutoryRulesEngine:
    """Pluggable engine that applies country-specific payroll deductions."""

    _plugins = {}

    @classmethod
    def register(cls, country_code, plugin_class):
        cls._plugins[country_code] = plugin_class

    @classmethod
    def get_plugin(cls, country_code):
        return cls._plugins.get(country_code)

    @classmethod
    def calculate(cls, country_code, gross_salary, basic_salary, employee_data=None):
        plugin = cls.get_plugin(country_code)
        if not plugin:
            return {'deductions': {}, 'employer_contributions': {}, 'net_salary': gross_salary}
        return plugin.calculate(gross_salary, basic_salary, employee_data or {})


# ======================== SRI LANKA ========================

class SriLankaPlugin:
    """Sri Lanka statutory: EPF (8%/12%), ETF (3%), APIT."""

    # APIT tax tables FY 2024/2025
    APIT_SLABS = [
        (100000, Decimal('0')),       # First 100K: exempt
        (41667, Decimal('0.06')),     # Next 41,667: 6%
        (41667, Decimal('0.12')),     # Next 41,667: 12%
        (41667, Decimal('0.18')),     # Next 41,667: 18%
        (41667, Decimal('0.24')),     # Next 41,667: 24%
        (41667, Decimal('0.30')),     # Next 41,667: 30%
        (None, Decimal('0.36')),      # Balance: 36%
    ]

    @classmethod
    def calculate(cls, gross_salary, basic_salary, employee_data):
        gross = Decimal(str(gross_salary))
        basic = Decimal(str(basic_salary))

        # EPF — Employee 8%, Employer 12%
        epf_employee = (basic * Decimal('0.08')).quantize(Decimal('0.01'))
        epf_employer = (basic * Decimal('0.12')).quantize(Decimal('0.01'))

        # ETF — Employer 3%
        etf_employer = (basic * Decimal('0.03')).quantize(Decimal('0.01'))

        # APIT — Progressive tax
        apit = cls._calculate_apit(gross)

        total_deductions = epf_employee + apit
        net_salary = (gross - total_deductions).quantize(Decimal('0.01'))

        return {
            'deductions': {
                'epf_employee': float(epf_employee),
                'apit': float(apit),
            },
            'employer_contributions': {
                'epf_employer': float(epf_employer),
                'etf_employer': float(etf_employer),
            },
            'net_salary': float(net_salary),
            'total_deductions': float(total_deductions),
            'total_employer_cost': float(gross + epf_employer + etf_employer),
        }

    @classmethod
    def _calculate_apit(cls, monthly_gross):
        tax = Decimal('0')
        remaining = monthly_gross
        for slab_limit, rate in cls.APIT_SLABS:
            if slab_limit is None:
                tax += remaining * rate
                break
            slab = min(remaining, Decimal(str(slab_limit)))
            tax += slab * rate
            remaining -= slab
            if remaining <= 0:
                break
        return tax.quantize(Decimal('0.01'))


# ======================== INDIA ========================

class IndiaPlugin:
    """India statutory: PF (12%/12%), ESI (0.75%/3.25%), TDS, Professional Tax."""

    PF_RATE_EMPLOYEE = Decimal('0.12')
    PF_RATE_EMPLOYER = Decimal('0.12')
    PF_CEILING = Decimal('15000')  # PF applicable on basic up to 15K

    ESI_EMPLOYEE = Decimal('0.0075')
    ESI_EMPLOYER = Decimal('0.0325')
    ESI_CEILING = Decimal('21000')  # ESI applicable if gross <= 21K

    # Professional Tax (varies by state, using Karnataka as default)
    PT_SLABS = [
        (15000, 0), (Decimal('999999999'), 200),
    ]

    # TDS (Old regime simplified slabs FY 2024-25)
    TDS_SLABS = [
        (300000, Decimal('0')),
        (300000, Decimal('0.05')),
        (300000, Decimal('0.10')),
        (300000, Decimal('0.15')),
        (300000, Decimal('0.20')),
        (None, Decimal('0.30')),
    ]

    @classmethod
    def calculate(cls, gross_salary, basic_salary, employee_data):
        gross = Decimal(str(gross_salary))
        basic = Decimal(str(basic_salary))

        # PF — on basic, capped at 15K
        pf_base = min(basic, cls.PF_CEILING)
        pf_employee = (pf_base * cls.PF_RATE_EMPLOYEE).quantize(Decimal('0.01'))
        pf_employer = (pf_base * cls.PF_RATE_EMPLOYER).quantize(Decimal('0.01'))

        # ESI — if gross <= 21K
        esi_employee = Decimal('0')
        esi_employer = Decimal('0')
        if gross <= cls.ESI_CEILING:
            esi_employee = (gross * cls.ESI_EMPLOYEE).quantize(Decimal('0.01'))
            esi_employer = (gross * cls.ESI_EMPLOYER).quantize(Decimal('0.01'))

        # Professional Tax
        pt = Decimal('200') if gross > 15000 else Decimal('0')

        # TDS (simplified monthly)
        annual_taxable = (gross * 12) - Decimal('50000')  # Standard deduction
        annual_tax = cls._calculate_tds(max(annual_taxable, Decimal('0')))
        tds_monthly = (annual_tax / 12).quantize(Decimal('0.01'))

        total_deductions = pf_employee + esi_employee + pt + tds_monthly
        net_salary = (gross - total_deductions).quantize(Decimal('0.01'))

        return {
            'deductions': {
                'pf_employee': float(pf_employee),
                'esi_employee': float(esi_employee),
                'professional_tax': float(pt),
                'tds': float(tds_monthly),
            },
            'employer_contributions': {
                'pf_employer': float(pf_employer),
                'esi_employer': float(esi_employer),
            },
            'net_salary': float(net_salary),
            'total_deductions': float(total_deductions),
            'total_employer_cost': float(gross + pf_employer + esi_employer),
        }

    @classmethod
    def _calculate_tds(cls, annual_taxable):
        tax = Decimal('0')
        remaining = annual_taxable
        for slab_limit, rate in cls.TDS_SLABS:
            if slab_limit is None:
                tax += remaining * rate
                break
            slab = min(remaining, Decimal(str(slab_limit)))
            tax += slab * rate
            remaining -= slab
            if remaining <= 0:
                break
        # Add 4% cess
        tax = tax * Decimal('1.04')
        return tax.quantize(Decimal('0.01'))


# ======================== UAE ========================

class UAEPlugin:
    """UAE statutory: No income tax. WPS compliance, gratuity, visa tracking."""

    @classmethod
    def calculate(cls, gross_salary, basic_salary, employee_data):
        gross = Decimal(str(gross_salary))
        basic = Decimal(str(basic_salary))

        # UAE has no income tax
        # Gratuity accrual (21 days per year for first 5 years, 30 days after)
        years_of_service = Decimal(str(employee_data.get('years_of_service', 0)))
        daily_basic = basic / 30

        if years_of_service <= 5:
            monthly_gratuity_accrual = (daily_basic * 21 / 12).quantize(Decimal('0.01'))
        else:
            monthly_gratuity_accrual = (daily_basic * 30 / 12).quantize(Decimal('0.01'))

        # DEWS (Difc Employees Workplace Savings) — optional
        dews_employee = Decimal('0')
        dews_employer = Decimal('0')
        if employee_data.get('difc_employee'):
            dews_employee = (basic * Decimal('0.055')).quantize(Decimal('0.01'))
            dews_employer = (basic * Decimal('0.055')).quantize(Decimal('0.01'))

        return {
            'deductions': {
                'income_tax': 0,  # No income tax in UAE
                'dews_employee': float(dews_employee),
            },
            'employer_contributions': {
                'gratuity_accrual': float(monthly_gratuity_accrual),
                'dews_employer': float(dews_employer),
            },
            'net_salary': float(gross - dews_employee),
            'total_deductions': float(dews_employee),
            'total_employer_cost': float(gross + monthly_gratuity_accrual + dews_employer),
            'wps_compliant': True,
            'visa_status': employee_data.get('visa_status', 'active'),
        }


# ======================== MULTI-CURRENCY ========================

class ExchangeRate:
    """Simple exchange rate conversion with cache."""

    _rates = {
        'USD_LKR': Decimal('325.00'),
        'USD_INR': Decimal('83.50'),
        'USD_AED': Decimal('3.67'),
        'GBP_USD': Decimal('1.27'),
        'EUR_USD': Decimal('1.09'),
        'LKR_USD': Decimal('0.00308'),
        'INR_USD': Decimal('0.01198'),
        'AED_USD': Decimal('0.2725'),
    }

    @classmethod
    def convert(cls, amount, from_currency, to_currency):
        if from_currency == to_currency:
            return Decimal(str(amount))

        key = f"{from_currency}_{to_currency}"
        rate = cls._rates.get(key)
        if rate:
            return (Decimal(str(amount)) * rate).quantize(Decimal('0.01'))

        # Try via USD
        to_usd = cls._rates.get(f"{from_currency}_USD")
        from_usd = cls._rates.get(f"USD_{to_currency}")
        if to_usd and from_usd:
            return (Decimal(str(amount)) * to_usd * from_usd).quantize(Decimal('0.01'))

        raise ValueError(f"No exchange rate for {from_currency} → {to_currency}")

    @classmethod
    def update_rate(cls, from_currency, to_currency, rate):
        cls._rates[f"{from_currency}_{to_currency}"] = Decimal(str(rate))


# Register plugins
StatutoryRulesEngine.register('LKA', SriLankaPlugin)
StatutoryRulesEngine.register('IND', IndiaPlugin)
StatutoryRulesEngine.register('ARE', UAEPlugin)
