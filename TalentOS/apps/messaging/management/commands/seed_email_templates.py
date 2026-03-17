"""
Seed default system email templates for all tenants.
Run: python manage.py seed_email_templates
"""
from django.core.management.base import BaseCommand

TEMPLATES = [
    {
        'name': 'Application Received',
        'slug': 'application_received',
        'subject': 'We received your application for {{job_title}}',
        'body': """Dear {{candidate_name}},

Thank you for applying for the {{job_title}} position at {{company_name}}.

We have received your application and will review it carefully. You will hear from us within 5-7 business days.

Best regards,
{{company_name}} Recruitment Team""",
    },
    {
        'name': 'Interview Invitation',
        'slug': 'interview_invite',
        'subject': 'Interview Invitation — {{job_title}} at {{company_name}}',
        'body': """Dear {{candidate_name}},

We are pleased to invite you for a {{interview_type}} interview for the {{job_title}} position.

Date & Time: {{interview_datetime}}
Format: {{interview_format}}
{{video_link_section}}

Please confirm your availability by replying to this email.

Best regards,
{{interviewer_name}}
{{company_name}}""",
    },
    {
        'name': 'Application Rejected',
        'slug': 'rejection',
        'subject': 'Update on your application for {{job_title}}',
        'body': """Dear {{candidate_name}},

Thank you for your interest in the {{job_title}} position at {{company_name}} and for taking the time to go through our recruitment process.

After careful consideration, we have decided to move forward with other candidates whose experience more closely matches our current requirements.

We will keep your profile on file for future opportunities.

Best regards,
{{company_name}} Recruitment Team""",
    },
    {
        'name': 'Offer Letter',
        'slug': 'offer_letter',
        'subject': 'Job Offer — {{job_title}} at {{company_name}}',
        'body': """Dear {{candidate_name}},

We are delighted to offer you the position of {{job_title}} at {{company_name}}.

Salary: {{salary}} {{currency}} per annum
Start Date: {{start_date}}
Employment Type: {{employment_type}}

Please review the attached offer letter and confirm your acceptance by {{offer_expiry_date}}.

We look forward to welcoming you to the team!

Best regards,
{{hiring_manager_name}}
{{company_name}}""",
    },
    {
        'name': 'Offer Accepted Confirmation',
        'slug': 'offer_accepted',
        'subject': 'Offer Accepted — Welcome to {{company_name}}!',
        'body': """Dear {{candidate_name}},

We are thrilled that you have accepted our offer for the {{job_title}} position!

Your start date is {{start_date}}. Our HR team will be in touch with onboarding details.

We look forward to having you on the team.

Best regards,
{{company_name}}""",
    },
    {
        'name': 'Onboarding Welcome',
        'slug': 'onboarding_welcome',
        'subject': 'Welcome to {{company_name}} — Your Onboarding Details',
        'body': """Dear {{candidate_name}},

Welcome to {{company_name}}! We are excited to have you join us on {{start_date}}.

Please find your onboarding checklist here: {{onboarding_link}}

If you have any questions before your start date, please contact {{hr_contact_email}}.

See you soon!
{{company_name}} HR Team""",
    },
]


class Command(BaseCommand):
    help = 'Seed default email templates'

    def handle(self, *args, **options):
        try:
            from apps.messaging.models import EmailTemplate
        except ImportError:
            self.stdout.write(self.style.WARNING('EmailTemplate model not found — skipping'))
            return

        created = 0
        for tpl in TEMPLATES:
            _, was_created = EmailTemplate.objects.get_or_create(
                slug=tpl['slug'],
                defaults={
                    'name': tpl['name'],
                    'subject': tpl['subject'],
                    'body': tpl['body'],
                    'is_system': True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {created} new email templates'))
