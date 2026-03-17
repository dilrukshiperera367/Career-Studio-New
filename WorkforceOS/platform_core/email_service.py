"""
Email notification service — sends templated emails for HR events.
Supports: leave approvals, payroll, onboarding tasks, announcements, etc.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# ============ EMAIL TEMPLATES (inline for portability) ============

TEMPLATES = {
    'leave_approved': {
        'subject': 'Leave Request Approved',
        'body': 'Hi {employee_name},\n\nYour {leave_type} leave from {start_date} to {end_date} has been approved by {approver_name}.\n\nRegards,\n{company_name} HR',
    },
    'leave_rejected': {
        'subject': 'Leave Request Rejected',
        'body': 'Hi {employee_name},\n\nYour {leave_type} leave from {start_date} to {end_date} has been rejected.\nReason: {reason}\n\nRegards,\n{company_name} HR',
    },
    'leave_request': {
        'subject': 'New Leave Request Pending Approval',
        'body': 'Hi {approver_name},\n\n{employee_name} has requested {leave_type} leave from {start_date} to {end_date} ({days} days).\n\nPlease review this request in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'payslip_ready': {
        'subject': 'Your Payslip is Ready - {period}',
        'body': 'Hi {employee_name},\n\nYour payslip for {period} is now available. Log in to ConnectHR to view and download it.\n\nNet Pay: {currency} {net_pay}\n\nRegards,\n{company_name} HR',
    },
    'onboarding_task': {
        'subject': 'Onboarding Task Assigned: {task_title}',
        'body': 'Hi {assignee_name},\n\nA new onboarding task has been assigned to you:\n\nTask: {task_title}\nEmployee: {employee_name}\nDue Date: {due_date}\n\nPlease complete this task in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'announcement': {
        'subject': '{title}',
        'body': 'Hi {employee_name},\n\n{body}\n\nRegards,\n{company_name} HR',
    },
    'password_reset': {
        'subject': 'Password Reset Request',
        'body': 'Hi {user_name},\n\nWe received a password reset request for your ConnectHR account.\n\nClick the link below to reset your password:\n{reset_link}\n\nThis link expires in 24 hours.\n\nRegards,\n{company_name}',
    },
    'welcome': {
        'subject': 'Welcome to {company_name}!',
        'body': 'Hi {employee_name},\n\nWelcome to {company_name}! Your ConnectHR account has been created.\n\nEmail: {email}\nTemporary Password: {temp_password}\n\nPlease log in and change your password.\n\nRegards,\n{company_name} HR',
    },
    'approval_needed': {
        'subject': 'Action Required: {entity_type} Approval',
        'body': 'Hi {approver_name},\n\nA new {entity_type} request from {requester_name} requires your approval.\n\nPlease review it in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'review_assigned': {
        'subject': 'Performance Review Assigned - {cycle_name}',
        'body': 'Hi {employee_name},\n\nYou have been assigned a performance review for the "{cycle_name}" cycle.\n\nSelf-review deadline: {deadline}\n\nPlease complete your self-assessment in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'document_expiring': {
        'subject': 'Action Required: Your {document_title} expires in {days_remaining} days',
        'body': 'Hi {employee_name},\n\nThis is an automated reminder that your {document_title} is set to expire on {expiry_date} ({days_remaining} days from now).\n\nPlease contact HR or update your documents in ConnectHR as soon as possible to ensure compliance.\n\nRegards,\n{company_name} HR',
    },
    'certification_expiring': {
        'subject': 'Certification Expiring Soon: {certification_name}',
        'body': 'Hi {employee_name},\n\nYour certification "{certification_name}" is due to expire on {expiry_date} ({days_remaining} days from now).\n\nPlease arrange renewal to remain compliant.\n\nRegards,\n{company_name} HR',
    },
    'onboarding_task_due_soon': {
        'subject': 'Onboarding Task Due in {days_remaining} Days: {task_title}',
        'body': 'Hi,\n\nThis is a reminder that the onboarding task "{task_title}" for {employee_name} is due on {due_date} ({days_remaining} days from now).\n\nPlease complete it in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'onboarding_task_overdue': {
        'subject': 'Overdue Onboarding Task: {task_title}',
        'body': 'Hi {employee_name},\n\nThe onboarding task "{task_title}" was due on {due_date} and has not been completed.\n\nPlease complete it in ConnectHR as soon as possible.\n\nRegards,\n{company_name} HR',
    },
    'payroll_reminder': {
        'subject': 'Payroll Processing Reminder — {period}',
        'body': 'Hi {recipient_name},\n\nThis is a reminder that payroll for {period} is due to be processed by {deadline}.\n\nPlease log in to ConnectHR and complete any outstanding payroll actions.\n\nRegards,\n{company_name} HR',
    },
    'payslip_dispatch': {
        'subject': 'Payslips Dispatched for {period}',
        'body': 'Hi {recipient_name},\n\nPayslips for the period {period} have been dispatched to all employees.\n\nTotal payslips sent: {count}\n\nRegards,\n{company_name} HR',
    },
    'performance_review_due': {
        'subject': 'Performance Review Deadline Approaching — {cycle_name}',
        'body': 'Hi {manager_name},\n\nThis is a reminder that performance reviews for the "{cycle_name}" cycle are due on {deadline}.\n\n{pending_count} review(s) are still pending under your team.\n\nPlease complete them in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'performance_self_assessment_due': {
        'subject': 'Self-Assessment Due — {cycle_name}',
        'body': 'Hi {employee_name},\n\nYour self-assessment for the "{cycle_name}" performance review cycle is due on {deadline}.\n\nPlease complete it in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'probation_ending': {
        'subject': 'Probation Period Ending Soon — {employee_name}',
        'body': 'Hi {manager_name},\n\nThis is a reminder that {employee_name}\'s probation period ends on {probation_end_date} ({days_remaining} days from now).\n\nPlease initiate a confirmation or extension action in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'visa_permit_expiry': {
        'subject': 'Visa / Work Permit Expiring — {employee_name}',
        'body': 'Hi {recipient_name},\n\n{employee_name}\'s {document_type} is due to expire on {expiry_date} ({days_remaining} days from now).\n\nPlease take the necessary action to renew or update this document.\n\nRegards,\n{company_name} HR',
    },
    'merit_cycle_deadline': {
        'subject': 'Merit Cycle Deadline Approaching — {cycle_name}',
        'body': 'Hi {manager_name},\n\nThe merit cycle "{cycle_name}" has a submission deadline of {deadline}.\n\n{pending_count} merit recommendation(s) are still pending for your team.\n\nPlease complete them in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
    'policy_acknowledgement_reminder': {
        'subject': 'Policy Acknowledgement Required: {policy_title}',
        'body': 'Hi {employee_name},\n\nYou have not yet acknowledged the policy "{policy_title}", which was due on {due_date}.\n\nPlease log in to ConnectHR and acknowledge it at your earliest convenience.\n\nRegards,\n{company_name} HR',
    },
    'attrition_risk_alert': {
        'subject': 'Attrition Risk Alert — {employee_name}',
        'body': 'Hi {recipient_name},\n\nOur people analytics model has flagged {employee_name} as a high attrition risk (score: {risk_score}).\n\nKey factors: {risk_factors}\n\nPlease review and consider appropriate retention actions in ConnectHR.\n\nRegards,\n{company_name} HR',
    },
}


def send_notification_email(template_key, recipient_email, context=None, tenant=None):
    """
    Send a templated email notification.

    Args:
        template_key: key from TEMPLATES dict
        recipient_email: email address (str or list)
        context: dict of template variables
        tenant: Tenant object (for branding)
    """
    context = context or {}
    template = TEMPLATES.get(template_key)
    if not template:
        logger.warning(f"Email template '{template_key}' not found")
        return False

    # Set default company name from tenant
    if tenant and 'company_name' not in context:
        context['company_name'] = tenant.name

    context.setdefault('company_name', 'ConnectHR')

    try:
        subject = template['subject'].format(**context)
        body = template['body'].format(**context)
    except KeyError as e:
        logger.error(f"Missing template variable {e} for template '{template_key}'")
        return False

    recipients = [recipient_email] if isinstance(recipient_email, str) else recipient_email
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@connecthr.com')

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=False,
        )
        logger.info(f"Email sent: {template_key} → {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email '{template_key}' to {recipients}: {e}")
        return False


def send_bulk_notification_emails(template_key, recipients_with_context, tenant=None):
    """
    Send the same template to multiple recipients with individual context.

    Args:
        template_key: key from TEMPLATES dict
        recipients_with_context: list of (email, context_dict) tuples
        tenant: Tenant object
    """
    results = []
    for email, context in recipients_with_context:
        ok = send_notification_email(template_key, email, context, tenant)
        results.append((email, ok))
    return results


def create_and_send_notification(user, title, message, category='system',
                                  template_key=None, email_context=None, tenant=None):
    """
    Create an in-app notification AND optionally send an email.
    """
    from .models import Notification

    notif = Notification.objects.create(
        tenant=tenant or user.tenant,
        recipient=user,
        title=title,
        message=message,
        category=category,
    )

    if template_key and user.email:
        email_context = email_context or {}
        send_notification_email(template_key, user.email, email_context, tenant)

    return notif
