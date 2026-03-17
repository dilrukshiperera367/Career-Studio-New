"""
Payslip PDF generator using WeasyPrint.
Generates professional payslip documents from PayrollEntry data.
"""

import io
import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger('hrm')

PAYSLIP_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 15mm; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; color: #1a1a2e; line-height: 1.5; }

  .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #4f46e5; padding-bottom: 15px; margin-bottom: 20px; }
  .company-name { font-size: 22px; font-weight: 700; color: #4f46e5; }
  .company-sub { font-size: 10px; color: #64748b; margin-top: 2px; }
  .payslip-label { text-align: right; }
  .payslip-label h2 { font-size: 16px; color: #1e1e3f; text-transform: uppercase; letter-spacing: 2px; }
  .payslip-label p { font-size: 10px; color: #64748b; }

  .info-grid { display: flex; gap: 20px; margin-bottom: 20px; }
  .info-box { flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; }
  .info-box h4 { font-size: 9px; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; margin-bottom: 8px; }
  .info-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
  .info-label { color: #64748b; font-size: 10px; }
  .info-value { font-weight: 600; font-size: 10px; }

  .earnings-deductions { display: flex; gap: 20px; margin-bottom: 20px; }
  .section { flex: 1; }
  .section-title { font-size: 12px; font-weight: 700; color: #1e1e3f; padding: 8px 12px; background: #f1f5f9; border-radius: 6px 6px 0 0; border: 1px solid #e2e8f0; border-bottom: none; }
  table { width: 100%; border-collapse: collapse; border: 1px solid #e2e8f0; }
  th { padding: 6px 12px; text-align: left; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; background: #fafbfc; border-bottom: 1px solid #e2e8f0; }
  th:last-child { text-align: right; }
  td { padding: 6px 12px; font-size: 10px; border-bottom: 1px solid #f1f5f9; }
  td:last-child { text-align: right; font-family: 'Courier New', monospace; font-weight: 600; }
  .subtotal td { font-weight: 700; background: #f8fafc; border-top: 2px solid #e2e8f0; font-size: 11px; }

  .net-pay { text-align: center; margin: 25px 0; padding: 20px; background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); border-radius: 10px; color: white; }
  .net-pay-label { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.8; }
  .net-pay-amount { font-size: 32px; font-weight: 800; margin-top: 5px; font-family: 'Courier New', monospace; }
  .net-pay-words { font-size: 9px; opacity: 0.7; margin-top: 5px; font-style: italic; }

  .statutory { margin-bottom: 20px; }
  .statutory table { width: 60%; margin: 0 auto; }
  .statutory .section-title { text-align: center; }

  .footer { border-top: 1px solid #e2e8f0; padding-top: 15px; margin-top: 20px; display: flex; justify-content: space-between; font-size: 9px; color: #94a3b8; }
  .confidential { color: #ef4444; font-weight: 600; font-size: 8px; text-transform: uppercase; letter-spacing: 1px; }
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="company-name">{{ company_name }}</div>
      <div class="company-sub">{{ company_legal_name }}</div>
      <div class="company-sub">{{ company_address }}</div>
    </div>
    <div class="payslip-label">
      <h2>Payslip</h2>
      <p>{{ period_label }}</p>
    </div>
  </div>

  <div class="info-grid">
    <div class="info-box">
      <h4>Employee Details</h4>
      <div class="info-row"><span class="info-label">Name</span><span class="info-value">{{ employee_name }}</span></div>
      <div class="info-row"><span class="info-label">Employee #</span><span class="info-value">{{ employee_number }}</span></div>
      <div class="info-row"><span class="info-label">Department</span><span class="info-value">{{ department }}</span></div>
      <div class="info-row"><span class="info-label">Position</span><span class="info-value">{{ position }}</span></div>
    </div>
    <div class="info-box">
      <h4>Payment Details</h4>
      <div class="info-row"><span class="info-label">Pay Period</span><span class="info-value">{{ period_label }}</span></div>
      <div class="info-row"><span class="info-label">Days Worked</span><span class="info-value">{{ days_worked }}</span></div>
      <div class="info-row"><span class="info-label">Days Absent</span><span class="info-value">{{ days_absent }}</span></div>
      <div class="info-row"><span class="info-label">OT Hours</span><span class="info-value">{{ ot_hours }}</span></div>
    </div>
    <div class="info-box">
      <h4>Bank Information</h4>
      <div class="info-row"><span class="info-label">Bank</span><span class="info-value">{{ bank_name }}</span></div>
      <div class="info-row"><span class="info-label">Branch</span><span class="info-value">{{ bank_branch }}</span></div>
      <div class="info-row"><span class="info-label">Account #</span><span class="info-value">{{ account_no }}</span></div>
    </div>
  </div>

  <div class="earnings-deductions">
    <div class="section">
      <div class="section-title">💰 Earnings</div>
      <table>
        <thead><tr><th>Component</th><th>Amount (LKR)</th></tr></thead>
        <tbody>
          <tr><td>Basic Salary</td><td>{{ basic_salary }}</td></tr>
          {{ earnings_rows }}
          {% if ot_amount > 0 %}
          <tr><td>Overtime ({{ ot_hours }}h × 1.5x)</td><td>{{ ot_amount }}</td></tr>
          {% endif %}
          <tr class="subtotal"><td>Total Earnings</td><td>{{ total_earnings }}</td></tr>
        </tbody>
      </table>
    </div>

    <div class="section">
      <div class="section-title">📉 Deductions</div>
      <table>
        <thead><tr><th>Component</th><th>Amount (LKR)</th></tr></thead>
        <tbody>
          {{ deduction_rows }}
          <tr><td>EPF Employee (8%)</td><td>{{ epf_employee }}</td></tr>
          <tr><td>APIT (Income Tax)</td><td>{{ apit }}</td></tr>
          {{ loan_rows }}
          <tr class="subtotal"><td>Total Deductions</td><td>{{ total_deductions }}</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="net-pay">
    <div class="net-pay-label">Net Pay</div>
    <div class="net-pay-amount">LKR {{ net_salary }}</div>
  </div>

  <div class="statutory">
    <div class="section-title">🏛️ Employer Statutory Contributions (Not deducted from pay)</div>
    <table>
      <thead><tr><th>Component</th><th>Amount (LKR)</th></tr></thead>
      <tbody>
        <tr><td>EPF Employer (12%)</td><td>{{ epf_employer }}</td></tr>
        <tr><td>ETF Employer (3%)</td><td>{{ etf_employer }}</td></tr>
        <tr class="subtotal"><td>Total Employer Cost</td><td>{{ employer_total_cost }}</td></tr>
      </tbody>
    </table>
  </div>

  <div class="footer">
    <span class="confidential">⚠ Confidential — For employee use only</span>
    <span>Generated by ConnectHR • {{ generated_date }}</span>
  </div>
</body>
</html>
"""


def format_lkr(value):
    """Format a number as LKR currency string."""
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def generate_payslip_html(entry):
    """Generate payslip HTML from a PayrollEntry object."""
    employee = entry.employee
    company = employee.company
    bank = employee.bank_details or {}

    # Build earnings rows
    earnings_rows = ""
    for e in (entry.earnings_json or []):
        earnings_rows += f'<tr><td>{e["component"]}</td><td>{format_lkr(e["amount"])}</td></tr>\n'

    # Build deduction rows
    deduction_rows = ""
    for d in (entry.deductions_json or []):
        deduction_rows += f'<tr><td>{d["component"]}</td><td>{format_lkr(d["amount"])}</td></tr>\n'

    # Build loan rows
    loan_rows = ""
    for lr in (entry.loan_deductions or []):
        loan_rows += f'<tr><td>Loan Deduction</td><td>{format_lkr(lr["amount"])}</td></tr>\n'

    # Address
    addr = company.address if hasattr(company, 'address') and company.address else {}
    address_str = f"{addr.get('line1', '')}, {addr.get('city', '')}" if addr else ""

    html = PAYSLIP_HTML_TEMPLATE
    replacements = {
        '{{ company_name }}': company.name if company else 'Company',
        '{{ company_legal_name }}': company.legal_name if company else '',
        '{{ company_address }}': address_str,
        '{{ period_label }}': f"{entry.payroll_run.period_year}-{entry.payroll_run.period_month:02d}",
        '{{ employee_name }}': employee.full_name,
        '{{ employee_number }}': employee.employee_number or '',
        '{{ department }}': employee.department.name if employee.department else '—',
        '{{ position }}': employee.position.title if employee.position else '—',
        '{{ days_worked }}': str(entry.days_worked or 0),
        '{{ days_absent }}': str(entry.days_absent or 0),
        '{{ ot_hours }}': str(float(entry.ot_hours or 0)),
        '{{ bank_name }}': bank.get('bank_name', '—'),
        '{{ bank_branch }}': bank.get('branch', '—'),
        '{{ account_no }}': bank.get('account_no', '—'),
        '{{ basic_salary }}': format_lkr(entry.basic_salary),
        '{{ earnings_rows }}': earnings_rows,
        '{{ ot_amount }}': format_lkr(entry.ot_amount),
        '{{ total_earnings }}': format_lkr(entry.total_earnings),
        '{{ deduction_rows }}': deduction_rows,
        '{{ epf_employee }}': format_lkr(entry.epf_employee),
        '{{ apit }}': format_lkr(entry.apit),
        '{{ loan_rows }}': loan_rows,
        '{{ total_deductions }}': format_lkr(entry.total_deductions),
        '{{ net_salary }}': format_lkr(entry.net_salary),
        '{{ epf_employer }}': format_lkr(entry.epf_employer),
        '{{ etf_employer }}': format_lkr(entry.etf_employer),
        '{{ employer_total_cost }}': format_lkr(entry.employer_total_cost),
        '{{ generated_date }}': date.today().strftime('%Y-%m-%d'),
    }

    # Handle conditional OT
    if float(entry.ot_amount or 0) <= 0:
        html = html.replace('{% if ot_amount > 0 %}', '<!-- ').replace('{% endif %}', ' -->')
    else:
        html = html.replace('{% if ot_amount > 0 %}', '').replace('{% endif %}', '')

    for key, val in replacements.items():
        html = html.replace(key, val)

    return html


def generate_payslip_pdf(entry):
    """Generate payslip PDF bytes from a PayrollEntry."""
    try:
        from weasyprint import HTML
        html_content = generate_payslip_html(entry)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        logger.warning("WeasyPrint not installed — returning HTML as fallback")
        return generate_payslip_html(entry).encode('utf-8')
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise
