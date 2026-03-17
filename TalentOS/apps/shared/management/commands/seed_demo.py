"""
Seed a full demo tenant with realistic data for ATS.
Usage: python manage.py seed_demo
Demo credentials: admin@demo.connectos.io / Demo@1234
"""
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create demo tenant with sample data for ATS. Login: admin@demo.connectos.io / Demo@1234'

    DEMO_TENANT_SLUG = 'demo'
    DEMO_EMAIL = 'admin@demo.connectos.io'
    DEMO_PASSWORD = 'Demo@1234'

    def handle(self, *args, **options):
        from apps.tenants.models import Tenant
        from apps.accounts.models import User

        self.stdout.write(self.style.MIGRATE_HEADING('Creating ATS demo tenant...'))

        # Create or get demo tenant
        tenant, created = Tenant.objects.get_or_create(
            slug=self.DEMO_TENANT_SLUG,
            defaults={
                'name': 'Demo Company Ltd',
                'plan': 'professional',
                'status': 'trial',
            }
        )
        if created:
            self.stdout.write(f'  + Tenant: {tenant.name}')
        else:
            self.stdout.write(f'  = Tenant exists: {tenant.name}')

        # Create admin user
        UserModel = get_user_model()
        user, created = UserModel.objects.get_or_create(
            email=self.DEMO_EMAIL,
            defaults={
                'tenant': tenant,
                'first_name': 'Demo',
                'last_name': 'Admin',
                'role': 'admin',
                'is_active': True,
            }
        )
        if created:
            user.set_password(self.DEMO_PASSWORD)
            user.save()
            self.stdout.write(f'  + Admin: {self.DEMO_EMAIL}')
        else:
            # Always reset password on re-run
            user.set_password(self.DEMO_PASSWORD)
            user.save()
            self.stdout.write(f'  = Admin exists, password reset: {self.DEMO_EMAIL}')

        # Seed sample jobs
        try:
            from apps.jobs.models import Job
            jobs_data = [
                {'title': 'Senior Software Engineer', 'department': 'Engineering', 'location': 'Colombo, LK', 'status': 'open'},
                {'title': 'Product Manager', 'department': 'Product', 'location': 'Remote', 'status': 'open'},
                {'title': 'UI/UX Designer', 'department': 'Design', 'location': 'Colombo, LK', 'status': 'open'},
                {'title': 'DevOps Engineer', 'department': 'Engineering', 'location': 'Colombo, LK', 'status': 'open'},
                {'title': 'Data Analyst', 'department': 'Analytics', 'location': 'Remote', 'status': 'closed'},
            ]
            created_count = 0
            for j in jobs_data:
                _, c = Job.objects.get_or_create(
                    tenant=tenant, title=j['title'],
                    defaults={**j, 'description': f'We are hiring a {j["title"]} to join our team.', 'created_by': user}
                )
                if c: created_count += 1
            self.stdout.write(f'  + Jobs: {created_count} created')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ! Jobs skipped: {e}'))

        # Seed sample candidates
        try:
            from apps.candidates.models import Candidate
            candidates_data = [
                {'full_name': 'Kasun Perera', 'primary_email': 'kasun@example.com', 'headline': 'Senior Software Engineer', 'location': 'Colombo'},
                {'full_name': 'Nimali Fernando', 'primary_email': 'nimali@example.com', 'headline': 'Product Manager', 'location': 'Kandy'},
                {'full_name': 'Ranil Silva', 'primary_email': 'ranil@example.com', 'headline': 'UI/UX Designer', 'location': 'Remote'},
                {'full_name': 'Priya Nair', 'primary_email': 'priya@example.com', 'headline': 'DevOps Engineer', 'location': 'Colombo'},
                {'full_name': 'Arjun Kumar', 'primary_email': 'arjun@example.com', 'headline': 'Data Scientist', 'location': 'Colombo'},
            ]
            c_count = 0
            for c in candidates_data:
                _, cr = Candidate.objects.get_or_create(
                    tenant=tenant, primary_email=c['primary_email'],
                    defaults={**c, 'status': 'active', 'source': 'demo'}
                )
                if cr: c_count += 1
            self.stdout.write(f'  + Candidates: {c_count} created')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ! Candidates skipped: {e}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ ATS Demo setup complete!'))
        self.stdout.write('')
        self.stdout.write('  Demo Login Credentials:')
        self.stdout.write(f'  URL:      http://localhost:3000')
        self.stdout.write(f'  Email:    {self.DEMO_EMAIL}')
        self.stdout.write(f'  Password: {self.DEMO_PASSWORD}')
        self.stdout.write('')
