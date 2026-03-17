"""Seed default HRM email templates."""
from django.core.management.base import BaseCommand

HRM_TEMPLATES = [
    {'slug': 'leave_approved', 'name': 'Leave Approved', 'subject': 'Your leave request has been approved', 'body': 'Dear {{employee_name}},\n\nYour {{leave_type}} from {{start_date}} to {{end_date}} ({{days}} days) has been approved.\n\nApproved by: {{approver_name}}\n\nHR Team'},
    {'slug': 'leave_rejected', 'name': 'Leave Rejected', 'subject': 'Your leave request has been rejected', 'body': 'Dear {{employee_name}},\n\nYour {{leave_type}} from {{start_date}} to {{end_date}} has been rejected.\n\nReason: {{rejection_reason}}\n\nHR Team'},
    {'slug': 'onboarding_assigned', 'name': 'Onboarding Assigned', 'subject': 'Your onboarding checklist is ready', 'body': 'Dear {{employee_name}},\n\nWelcome to {{company_name}}! Your onboarding tasks have been assigned.\n\nAccess your checklist at: {{onboarding_link}}\n\nHR Team'},
    {'slug': 'payslip_ready', 'name': 'Payslip Ready', 'subject': 'Your payslip for {{period}} is ready', 'body': 'Dear {{employee_name}},\n\nYour payslip for {{period}} is ready for download.\n\nNet Pay: {{currency}} {{net_pay}}\n\nView at: {{portal_link}}\n\nHR Team'},
    {'slug': 'approval_required', 'name': 'Approval Required', 'subject': 'Action Required: {{request_type}} pending your approval', 'body': 'Dear {{approver_name}},\n\n{{employee_name}} has submitted a {{request_type}} that requires your approval.\n\nDetails: {{details}}\n\nApprove or reject at: {{approval_link}}\n\nHR Team'},
    {'slug': 'anniversary_reminder', 'name': 'Work Anniversary', 'subject': 'Happy {{years}}-Year Work Anniversary, {{employee_name}}!', 'body': 'Dear {{employee_name}},\n\nCongratulations on your {{years}}-year work anniversary at {{company_name}}!\n\nThank you for your continued contribution.\n\nHR Team'},
    {'slug': 'probation_review', 'name': 'Probation Review Due', 'subject': 'Probation Review Due — {{employee_name}}', 'body': 'Dear {{manager_name}},\n\n{{employee_name}} is completing their probation period on {{probation_end_date}}.\n\nPlease submit your performance review by: {{review_deadline}}\n\nHR Team'},
    {'slug': 'helpdesk_ticket_opened', 'name': 'Helpdesk Ticket Opened', 'subject': '[{{ticket_number}}] Your HR helpdesk ticket has been received', 'body': 'Dear {{employee_name}},\n\nYour helpdesk ticket {{ticket_number}} has been received.\n\nSubject: {{subject}}\nPriority: {{priority}}\n\nYou will receive updates as the ticket progresses.\n\nHR Team'},
]


class Command(BaseCommand):
    help = 'Seed HRM email templates'

    def handle(self, *args, **options):
        try:
            from platform_core.models import EmailTemplate
        except ImportError:
            try:
                from platform_core.notification_models import EmailTemplate
            except ImportError:
                self.stdout.write(self.style.WARNING('EmailTemplate not found in platform_core'))
                return

        created = 0
        for tpl in HRM_TEMPLATES:
            _, was_created = EmailTemplate.objects.get_or_create(
                slug=tpl['slug'],
                defaults={k: v for k, v in tpl.items() if k != 'slug'},
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} HRM templates'))
