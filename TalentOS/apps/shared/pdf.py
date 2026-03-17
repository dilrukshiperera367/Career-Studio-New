"""
PDF generation utilities for offer letters and reports.
Uses weasyprint if available, falls back to plain-text HTML response.
"""
from __future__ import annotations

import logging
from datetime import date
from django.http import HttpResponse
from django.template import Template, Context

logger = logging.getLogger(__name__)

OFFER_LETTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #333; }
  .header { text-align: center; padding: 40px 0 20px; border-bottom: 2px solid #4F46E5; margin-bottom: 30px; }
  .company-name { font-size: 22pt; font-weight: 700; color: #4F46E5; }
  .title { font-size: 16pt; font-weight: 600; margin-top: 8px; color: #374151; }
  .date { font-size: 10pt; color: #6B7280; margin-top: 4px; }
  .body { padding: 0 40px; }
  .section { margin-bottom: 24px; }
  .section h2 { font-size: 11pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #374151; margin-bottom: 8px; border-bottom: 1px solid #E5E7EB; padding-bottom: 4px; }
  .detail-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #F3F4F6; }
  .detail-label { font-weight: 600; color: #6B7280; }
  .detail-value { color: #111827; }
  p { margin-bottom: 12px; color: #374151; }
  .signature-block { margin-top: 48px; display: flex; justify-content: space-between; }
  .sig-line { width: 45%; border-top: 1px solid #374151; padding-top: 8px; font-size: 9pt; color: #6B7280; }
  .footer { margin-top: 60px; text-align: center; font-size: 9pt; color: #9CA3AF; border-top: 1px solid #E5E7EB; padding-top: 12px; }
</style>
</head>
<body>
  <div class="header">
    <div class="company-name">{{ company_name }}</div>
    <div class="title">Offer of Employment</div>
    <div class="date">{{ offer_date }}</div>
  </div>
  <div class="body">
    <div class="section">
      <p>Dear {{ candidate_name }},</p>
      <p>{{ company_name }} is pleased to extend this offer of employment for the position of <strong>{{ job_title }}</strong>. We are excited about the skills and experience you bring, and we look forward to welcoming you to our team.</p>
    </div>
    <div class="section">
      <h2>Offer Details</h2>
      <div class="detail-row"><span class="detail-label">Position</span><span class="detail-value">{{ job_title }}</span></div>
      <div class="detail-row"><span class="detail-label">Department</span><span class="detail-value">{{ department }}</span></div>
      <div class="detail-row"><span class="detail-label">Start Date</span><span class="detail-value">{{ start_date }}</span></div>
      <div class="detail-row"><span class="detail-label">Salary</span><span class="detail-value">{{ salary }}</span></div>
      <div class="detail-row"><span class="detail-label">Employment Type</span><span class="detail-value">{{ employment_type }}</span></div>
      {% if location %}<div class="detail-row"><span class="detail-label">Location</span><span class="detail-value">{{ location }}</span></div>{% endif %}
    </div>
    <div class="section">
      <p>This offer is contingent upon successful completion of background verification and reference checks.</p>
      <p>Please sign and return this offer letter by <strong>{{ expiry_date }}</strong> to confirm your acceptance.</p>
    </div>
    <div class="signature-block">
      <div class="sig-line">Authorized Signature &amp; Date</div>
      <div class="sig-line">Candidate Signature &amp; Date</div>
    </div>
  </div>
  <div class="footer">{{ company_name }} · Confidential Offer Letter · Generated {{ offer_date }}</div>
</body>
</html>
"""


def render_offer_pdf(context_data: dict) -> bytes | None:
    """
    Render an offer letter as PDF bytes.
    Falls back to None if weasyprint is unavailable.
    """
    html = Template(OFFER_LETTER_TEMPLATE).render(Context(context_data))
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except ImportError:
        logger.warning("weasyprint not installed — PDF generation unavailable. Install with: pip install weasyprint")
        return None
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        return None


def offer_letter_html_response(context_data: dict) -> HttpResponse:
    """Return the offer letter as a rendered HTML response (fallback when weasyprint unavailable)."""
    from django.template import Template, Context
    html = Template(OFFER_LETTER_TEMPLATE).render(Context(context_data))
    return HttpResponse(html, content_type='text/html')


def offer_letter_pdf_response(context_data: dict) -> HttpResponse:
    """Return an HttpResponse with PDF content for offer letter download."""
    pdf_bytes = render_offer_pdf(context_data)
    if pdf_bytes is None:
        return offer_letter_html_response(context_data)
    candidate_name = context_data.get('candidate_name', 'candidate').replace(' ', '_').lower()
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="offer_letter_{candidate_name}.pdf"'
    return response
