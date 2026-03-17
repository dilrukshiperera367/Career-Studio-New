"""
Seed a full demo tenant with realistic data for HRM.
Usage: python manage.py seed_demo
Demo credentials: admin@demo.connectos.io / Demo@1234
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create HRM demo tenant. Login: admin@demo.connectos.io / Demo@1234'

    DEMO_EMAIL = 'admin@demo.connectos.io'
    DEMO_PASSWORD = 'Demo@1234'
    DEMO_MANAGER_EMAIL = 'manager@demo.connectos.io'
    DEMO_EMPLOYEE_EMAIL = 'employee@demo.connectos.io'

    def handle(self, *args, **options):
        from tenants.models import Tenant
        from authentication.models import User

        self.stdout.write(self.style.MIGRATE_HEADING('Creating HRM demo tenant...'))

        tenant, _ = Tenant.objects.get_or_create(
            slug='demo',
            defaults={'name': 'Demo Company Ltd', 'plan': 'professional', 'status': 'trial'}
        )
        self.stdout.write(f'  = Tenant: {tenant.name}')

        UserModel = get_user_model()

        def ensure_user(email, first, last, role, password=None):
            u, created = UserModel.objects.get_or_create(
                email=email,
                defaults={'tenant': tenant, 'first_name': first, 'last_name': last, 'role': role, 'is_active': True}
            )
            u.set_password(password or self.DEMO_PASSWORD)
            u.save()
            return u, created

        admin_user, _ = ensure_user(self.DEMO_EMAIL, 'Admin', 'User', 'hr_admin')
        mgr_user, _   = ensure_user(self.DEMO_MANAGER_EMAIL, 'Manager', 'Demo', 'manager')
        emp_user, _   = ensure_user(self.DEMO_EMPLOYEE_EMAIL, 'Employee', 'Demo', 'employee')

        self.stdout.write(f'  + Users created')

        # Seed departments and employees
        try:
            from core_hr.models import Department, Employee, Company
            # Ensure a default company exists
            company, _ = Company.objects.get_or_create(
                tenant=tenant, name='Demo Company Ltd',
                defaults={'legal_name': 'Demo Company Ltd', 'country': 'LKA', 'currency': 'LKR'}
            )

            eng_dept, _ = Department.objects.get_or_create(
                tenant=tenant, name='Engineering',
                defaults={'code': 'ENG', 'company': company}
            )
            hr_dept, _ = Department.objects.get_or_create(
                tenant=tenant, name='Human Resources',
                defaults={'code': 'HR', 'company': company}
            )

            employees_data = [
                {'first_name': 'Kasun', 'last_name': 'Perera', 'work_email': 'kasun@demo.com', 'department': eng_dept, 'employment_type': 'full_time', 'status': 'active'},
                {'first_name': 'Nimali', 'last_name': 'Fernando', 'work_email': 'nimali@demo.com', 'department': hr_dept, 'employment_type': 'full_time', 'status': 'active'},
                {'first_name': 'Ranil', 'last_name': 'Silva', 'work_email': 'ranil@demo.com', 'department': eng_dept, 'employment_type': 'full_time', 'status': 'active'},
                {'first_name': 'Priya', 'last_name': 'Nair', 'work_email': 'priya@demo.com', 'department': eng_dept, 'employment_type': 'casual', 'status': 'active'},
                {'first_name': 'Arjun', 'last_name': 'Kumar', 'work_email': 'arjun@demo.com', 'department': hr_dept, 'employment_type': 'full_time', 'status': 'probation'},
            ]
            import datetime
            e_count = 0
            for e in employees_data:
                _, c = Employee.objects.get_or_create(
                    tenant=tenant, work_email=e['work_email'],
                    defaults={**e, 'company': company, 'hire_date': datetime.date(2023, 1, 1)}
                )
                if c: e_count += 1
            self.stdout.write(f'  + Employees: {e_count}')
        except Exception as ex:
            self.stdout.write(self.style.WARNING(f'  ! Employees skipped: {ex}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ HRM Demo setup complete!'))
        self.stdout.write('')
        self.stdout.write('  Demo Login Credentials:')
        self.stdout.write(f'  URL:         http://localhost:5173')
        self.stdout.write(f'  Admin:       {self.DEMO_EMAIL}  /  {self.DEMO_PASSWORD}')
        self.stdout.write(f'  Manager:     {self.DEMO_MANAGER_EMAIL}  /  {self.DEMO_PASSWORD}')
        self.stdout.write(f'  Employee:    {self.DEMO_EMPLOYEE_EMAIL}  /  {self.DEMO_PASSWORD}')
        self.stdout.write('')
