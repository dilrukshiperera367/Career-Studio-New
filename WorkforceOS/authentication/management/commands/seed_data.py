"""
Management command to seed demo data for the HRM system.
Creates a demo tenant, admin user, roles, permissions, org structure,
employees, leave types, shifts, salary structures, and statutory rules.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import uuid


class Command(BaseCommand):
    help = 'Seed demo data for HRM system'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding HRM demo data...\n')

        self._seed_permissions()
        self._seed_roles()
        tenant = self._seed_tenant()
        admin_user = self._seed_admin_user(tenant)
        company = self._seed_company(tenant)
        branches = self._seed_branches(tenant, company)
        departments = self._seed_departments(tenant, company)
        positions = self._seed_positions(tenant, departments)
        employees = self._seed_employees(tenant, company, departments, branches, positions, admin_user)
        self._seed_leave_types(tenant)
        self._seed_shifts(tenant)
        self._seed_salary_structures(tenant, company)
        self._seed_statutory_rules()
        self._seed_holiday_calendar(tenant)
        self._seed_onboarding_template(tenant)
        self._seed_email_templates(tenant)
        self._seed_workflow_templates(tenant)

        self.stdout.write(self.style.SUCCESS('✅ Done! Demo data seeded successfully.'))
        self.stdout.write(f'\n📧 Admin login: admin@demo.connecthr.com / Password123!')
        self.stdout.write(f'🏢 Tenant slug: demo-company\n')

    def _seed_permissions(self):
        from authentication.models import Permission

        perms = [
            ('employees.view', 'View employees', 'core_hr'),
            ('employees.create', 'Create employees', 'core_hr'),
            ('employees.edit', 'Edit employees', 'core_hr'),
            ('employees.delete', 'Delete employees', 'core_hr'),
            ('org.manage', 'Manage org structure', 'core_hr'),
            ('documents.manage', 'Manage documents', 'core_hr'),
            ('leave.view', 'View leave', 'leave'),
            ('leave.apply', 'Apply for leave', 'leave'),
            ('leave.approve', 'Approve leave', 'leave'),
            ('leave.manage', 'Manage leave policies', 'leave'),
            ('attendance.view', 'View attendance', 'attendance'),
            ('attendance.clock', 'Clock in/out', 'attendance'),
            ('attendance.manage', 'Manage attendance', 'attendance'),
            ('payroll.view', 'View payroll', 'payroll'),
            ('payroll.run', 'Process payroll', 'payroll'),
            ('payroll.approve', 'Approve payroll', 'payroll'),
            ('payroll.finalize', 'Finalize payroll', 'payroll'),
            ('performance.view', 'View performance', 'performance'),
            ('performance.review', 'Submit reviews', 'performance'),
            ('performance.manage', 'Manage review cycles', 'performance'),
            ('onboarding.manage', 'Manage onboarding', 'onboarding'),
            ('analytics.view', 'View analytics', 'analytics'),
            ('settings.manage', 'Manage settings', 'settings'),
        ]

        for codename, desc, category in perms:
            Permission.objects.get_or_create(
                codename=codename,
                defaults={'description': desc, 'category': category}
            )
        self.stdout.write(f'  ✓ {len(perms)} permissions created')

    def _seed_roles(self):
        from authentication.models import Role, Permission, RolePermission

        roles_config = {
            'Super Admin': {'perms': '__all__', 'scope': 'all'},
            'HR Manager': {'perms': ['employees', 'org', 'documents', 'leave', 'attendance', 'payroll', 'performance', 'onboarding', 'analytics'], 'scope': 'all'},
            'HR Officer': {'perms': ['employees.view', 'employees.create', 'employees.edit', 'documents.manage', 'leave', 'attendance', 'onboarding.manage'], 'scope': 'all'},
            'Department Manager': {'perms': ['employees.view', 'leave.view', 'leave.approve', 'attendance.view', 'performance.view', 'performance.review'], 'scope': 'department'},
            'Team Lead': {'perms': ['employees.view', 'leave.view', 'leave.approve', 'attendance.view', 'performance.view'], 'scope': 'team'},
            'Employee': {'perms': ['employees.view', 'leave.view', 'leave.apply', 'attendance.clock', 'performance.view'], 'scope': 'own'},
            'Payroll Admin': {'perms': ['payroll', 'employees.view', 'attendance.view'], 'scope': 'all'},
            'Finance': {'perms': ['payroll.view', 'analytics.view'], 'scope': 'all'},
            'Read Only': {'perms': ['employees.view', 'leave.view', 'attendance.view'], 'scope': 'all'},
        }

        all_perms = Permission.objects.all()

        for role_name, config in roles_config.items():
            role, _ = Role.objects.get_or_create(
                name=role_name,
                tenant=None,
                defaults={'is_system_role': True, 'description': f'System role: {role_name}'}
            )

            # Assign permissions
            if config['perms'] == '__all__':
                for perm in all_perms:
                    RolePermission.objects.get_or_create(
                        role=role, permission=perm,
                        defaults={'scope': config['scope']}
                    )
            else:
                for perm_prefix in config['perms']:
                    matching = all_perms.filter(codename__startswith=perm_prefix)
                    for perm in matching:
                        RolePermission.objects.get_or_create(
                            role=role, permission=perm,
                            defaults={'scope': config['scope']}
                        )

        self.stdout.write(f'  ✓ {len(roles_config)} roles created with permissions')

    def _seed_tenant(self):
        from tenants.models import Tenant, TenantFeature

        tenant, _ = Tenant.objects.get_or_create(
            slug='demo-company',
            defaults={
                'name': 'Demo Corporation (Pvt) Ltd',
                'plan': 'enterprise',
                'status': 'active',
                'max_employees': 500,
                'settings_json': {'branding': {'primary_color': '#4F46E5'}},
            }
        )

        # Enable all modules
        modules = ['core_hr', 'onboarding', 'leave_attendance', 'payroll',
                    'performance', 'compensation', 'engagement', 'learning',
                    'helpdesk', 'analytics', 'integrations']

        for mod in modules:
            TenantFeature.objects.get_or_create(
                tenant=tenant, module=mod,
                defaults={'tier': 'enterprise', 'enabled': True, 'enabled_at': timezone.now()}
            )

        self.stdout.write(f'  ✓ Tenant: {tenant.name}')
        return tenant

    def _seed_admin_user(self, tenant):
        from django.contrib.auth import get_user_model
        from authentication.models import Role, UserRole

        User = get_user_model()
        user, created = User.objects.get_or_create(
            email='admin@demo.connecthr.com',
            tenant=tenant,
            defaults={
                'first_name': 'System',
                'last_name': 'Admin',
                'is_staff': True,
                'status': 'active',
            }
        )
        if created:
            user.set_password('Password123!')
            user.save()
            admin_role = Role.objects.get(name='Super Admin')
            UserRole.objects.create(user=user, role=admin_role)

        self.stdout.write(f'  ✓ Admin user: {user.email}')
        return user

    def _seed_company(self, tenant):
        from core_hr.models import Company

        company, _ = Company.objects.get_or_create(
            tenant=tenant, name='Demo Corporation',
            defaults={
                'legal_name': 'Demo Corporation (Pvt) Ltd',
                'registration_no': 'PV00123456',
                'tax_id': '123456789',
                'country': 'LKA',
                'currency': 'LKR',
                'address': {
                    'line1': '42 Galle Road',
                    'city': 'Colombo 03',
                    'state': 'Western Province',
                    'country': 'LKA',
                    'postal_code': '00300',
                },
            }
        )
        self.stdout.write(f'  ✓ Company: {company.name}')
        return company

    def _seed_branches(self, tenant, company):
        from core_hr.models import Branch

        branches_data = [
            {'name': 'Head Office — Colombo', 'code': 'HO', 'address': {'city': 'Colombo 03'}, 'geo_coordinates': {'lat': 6.9271, 'lng': 79.8612, 'radius_m': 200}},
            {'name': 'Kandy Branch', 'code': 'KDY', 'address': {'city': 'Kandy'}, 'geo_coordinates': {'lat': 7.2906, 'lng': 80.6337, 'radius_m': 150}},
            {'name': 'Galle Branch', 'code': 'GLL', 'address': {'city': 'Galle'}, 'geo_coordinates': {'lat': 6.0535, 'lng': 80.2210, 'radius_m': 150}},
        ]

        branches = []
        for b in branches_data:
            branch, _ = Branch.objects.get_or_create(
                tenant=tenant, company=company, name=b['name'],
                defaults={**b}
            )
            branches.append(branch)

        self.stdout.write(f'  ✓ {len(branches)} branches created')
        return branches

    def _seed_departments(self, tenant, company):
        from core_hr.models import Department

        depts_data = [
            'Engineering', 'Human Resources', 'Finance & Accounting',
            'Sales & Marketing', 'Operations', 'Customer Support',
            'Product Management', 'Quality Assurance',
        ]

        departments = {}
        for name in depts_data:
            dept, _ = Department.objects.get_or_create(
                tenant=tenant, name=name,
                defaults={'company': company, 'status': 'active'}
            )
            departments[name] = dept

        self.stdout.write(f'  ✓ {len(departments)} departments created')
        return departments

    def _seed_positions(self, tenant, departments):
        from core_hr.models import Position

        positions_data = [
            ('Software Engineer', 'Engineering', 'L2', 'B2'),
            ('Senior Software Engineer', 'Engineering', 'L3', 'B3'),
            ('Engineering Manager', 'Engineering', 'L4', 'B4'),
            ('HR Manager', 'Human Resources', 'L4', 'B4'),
            ('HR Executive', 'Human Resources', 'L2', 'B2'),
            ('Accountant', 'Finance & Accounting', 'L2', 'B2'),
            ('Finance Manager', 'Finance & Accounting', 'L4', 'B4'),
            ('Sales Executive', 'Sales & Marketing', 'L2', 'B2'),
            ('Marketing Manager', 'Sales & Marketing', 'L3', 'B3'),
            ('Operations Manager', 'Operations', 'L4', 'B4'),
            ('QA Engineer', 'Quality Assurance', 'L2', 'B2'),
            ('Product Manager', 'Product Management', 'L3', 'B3'),
        ]

        positions = {}
        for title, dept_name, grade, band in positions_data:
            pos, _ = Position.objects.get_or_create(
                tenant=tenant, title=title,
                defaults={
                    'department': departments.get(dept_name),
                    'grade': grade, 'band': band,
                }
            )
            positions[title] = pos

        self.stdout.write(f'  ✓ {len(positions)} positions created')
        return positions

    def _seed_employees(self, tenant, company, departments, branches, positions, admin_user):
        from core_hr.models import Employee, JobHistory

        employees_data = [
            {'fn': 'Kasun', 'ln': 'Perera', 'email': 'kasun@demo.connecthr.com', 'dept': 'Engineering', 'pos': 'Engineering Manager', 'hire': '2019-03-15'},
            {'fn': 'Sachini', 'ln': 'Fernando', 'email': 'sachini@demo.connecthr.com', 'dept': 'Human Resources', 'pos': 'HR Manager', 'hire': '2019-06-01'},
            {'fn': 'Nuwan', 'ln': 'Silva', 'email': 'nuwan@demo.connecthr.com', 'dept': 'Engineering', 'pos': 'Senior Software Engineer', 'hire': '2020-01-10'},
            {'fn': 'Dilanka', 'ln': 'Jayawardena', 'email': 'dilanka@demo.connecthr.com', 'dept': 'Engineering', 'pos': 'Software Engineer', 'hire': '2021-07-01'},
            {'fn': 'Malini', 'ln': 'Wickramasinghe', 'email': 'malini@demo.connecthr.com', 'dept': 'Finance & Accounting', 'pos': 'Finance Manager', 'hire': '2018-11-20'},
            {'fn': 'Amara', 'ln': 'Gunaratne', 'email': 'amara@demo.connecthr.com', 'dept': 'Finance & Accounting', 'pos': 'Accountant', 'hire': '2022-03-01'},
            {'fn': 'Chaminda', 'ln': 'Bandara', 'email': 'chaminda@demo.connecthr.com', 'dept': 'Sales & Marketing', 'pos': 'Marketing Manager', 'hire': '2020-05-15'},
            {'fn': 'Rashmi', 'ln': 'De Mel', 'email': 'rashmi@demo.connecthr.com', 'dept': 'Sales & Marketing', 'pos': 'Sales Executive', 'hire': '2023-01-10'},
            {'fn': 'Tharindu', 'ln': 'Rajapaksha', 'email': 'tharindu@demo.connecthr.com', 'dept': 'Operations', 'pos': 'Operations Manager', 'hire': '2019-09-01'},
            {'fn': 'Nipuni', 'ln': 'Senaratne', 'email': 'nipuni@demo.connecthr.com', 'dept': 'Quality Assurance', 'pos': 'QA Engineer', 'hire': '2022-08-15'},
            {'fn': 'Lasith', 'ln': 'Karunaratne', 'email': 'lasith@demo.connecthr.com', 'dept': 'Engineering', 'pos': 'Software Engineer', 'hire': '2023-06-01'},
            {'fn': 'Ishara', 'ln': 'Dissanayake', 'email': 'ishara@demo.connecthr.com', 'dept': 'Human Resources', 'pos': 'HR Executive', 'hire': '2021-04-12'},
        ]

        employees = []
        for emp in employees_data:
            employee, created = Employee.objects.get_or_create(
                tenant=tenant, work_email=emp['email'],
                defaults={
                    'company': company,
                    'first_name': emp['fn'],
                    'last_name': emp['ln'],
                    'department': departments.get(emp['dept']),
                    'position': positions.get(emp['pos']),
                    'branch': branches[0],  # Head office
                    'hire_date': date.fromisoformat(emp['hire']),
                    'status': 'active',
                    'contract_type': 'permanent',
                    'employment_type': 'full_time',
                    'created_by': admin_user,
                }
            )
            if created:
                JobHistory.objects.create(
                    tenant=tenant,
                    employee=employee,
                    change_type='hire',
                    effective_date=employee.hire_date,
                    new_position=employee.position,
                    new_department=employee.department,
                    new_branch=employee.branch,
                )
            employees.append(employee)

        self.stdout.write(f'  ✓ {len(employees)} employees created')
        return employees

    def _seed_leave_types(self, tenant):
        from leave_attendance.models import LeaveType

        types = [
            {'name': 'Annual Leave', 'code': 'AL', 'max_days': 14, 'paid': True, 'carry': True, 'max_carry': 7, 'color': '#3B82F6'},
            {'name': 'Casual Leave', 'code': 'CL', 'max_days': 7, 'paid': True, 'carry': False, 'max_carry': 0, 'color': '#10B981'},
            {'name': 'Sick Leave', 'code': 'SL', 'max_days': 7, 'paid': True, 'carry': False, 'max_carry': 0, 'requires_attachment_after': 2, 'color': '#EF4444'},
            {'name': 'Maternity Leave', 'code': 'MAT', 'max_days': 84, 'paid': True, 'carry': False, 'max_carry': 0, 'gender': 'female', 'color': '#EC4899'},
            {'name': 'Paternity Leave', 'code': 'PAT', 'max_days': 3, 'paid': True, 'carry': False, 'max_carry': 0, 'gender': 'male', 'color': '#6366F1'},
            {'name': 'No-Pay Leave', 'code': 'NP', 'max_days': 30, 'paid': False, 'carry': False, 'max_carry': 0, 'color': '#9CA3AF'},
        ]

        for lt in types:
            LeaveType.objects.get_or_create(
                tenant=tenant, code=lt['code'],
                defaults={
                    'name': lt['name'],
                    'max_days_per_year': lt['max_days'],
                    'paid': lt['paid'],
                    'carry_forward': lt['carry'],
                    'max_carry_forward': lt['max_carry'],
                    'applicable_gender': lt.get('gender', ''),
                    'requires_attachment_after_days': lt.get('requires_attachment_after'),
                    'color': lt['color'],
                }
            )

        self.stdout.write(f'  ✓ {len(types)} leave types created')

    def _seed_shifts(self, tenant):
        from leave_attendance.models import ShiftTemplate

        shifts = [
            {'name': 'Day Shift', 'code': 'DAY', 'start': '08:30', 'end': '17:30', 'break': 60, 'grace': 15, 'hours': 8},
            {'name': 'Morning Shift', 'code': 'MRN', 'start': '06:00', 'end': '14:00', 'break': 30, 'grace': 10, 'hours': 7.5},
            {'name': 'Night Shift', 'code': 'NGT', 'start': '22:00', 'end': '06:00', 'break': 30, 'grace': 10, 'hours': 7.5, 'night': True},
        ]

        for s in shifts:
            ShiftTemplate.objects.get_or_create(
                tenant=tenant, code=s['code'],
                defaults={
                    'name': s['name'],
                    'start_time': s['start'],
                    'end_time': s['end'],
                    'break_minutes': s['break'],
                    'grace_minutes': s['grace'],
                    'working_hours': s['hours'],
                    'is_night_shift': s.get('night', False),
                }
            )
        self.stdout.write(f'  ✓ {len(shifts)} shift templates created')

    def _seed_salary_structures(self, tenant, company):
        from payroll.models import SalaryStructure

        structures = [
            {
                'name': 'Standard - Full Time',
                'components': [
                    {'name': 'Basic Salary', 'type': 'earning', 'calc_type': 'fixed', 'value': 0, 'basis': 'basic'},
                    {'name': 'Transport Allowance', 'type': 'earning', 'calc_type': 'fixed', 'value': 5000},
                    {'name': 'Meal Allowance', 'type': 'earning', 'calc_type': 'fixed', 'value': 3000},
                    {'name': 'Medical Allowance', 'type': 'earning', 'calc_type': 'percentage', 'value': 5, 'basis': 'basic'},
                ],
            },
            {
                'name': 'Manager Grade',
                'components': [
                    {'name': 'Basic Salary', 'type': 'earning', 'calc_type': 'fixed', 'value': 0, 'basis': 'basic'},
                    {'name': 'Transport Allowance', 'type': 'earning', 'calc_type': 'fixed', 'value': 10000},
                    {'name': 'Meal Allowance', 'type': 'earning', 'calc_type': 'fixed', 'value': 5000},
                    {'name': 'Medical Allowance', 'type': 'earning', 'calc_type': 'percentage', 'value': 10, 'basis': 'basic'},
                    {'name': 'Fuel Allowance', 'type': 'earning', 'calc_type': 'fixed', 'value': 15000},
                ],
            },
        ]

        for s in structures:
            SalaryStructure.objects.get_or_create(
                tenant=tenant, name=s['name'],
                defaults={'company': company, 'components': s['components']}
            )
        self.stdout.write(f'  ✓ {len(structures)} salary structures created')

    def _seed_statutory_rules(self):
        from payroll.models import StatutoryRule

        rules = [
            {
                'country': 'LKA', 'rule_type': 'epf_employee', 'name': 'EPF Employee Contribution',
                'calculation': {'type': 'percentage', 'rate': 0.08},
                'effective_from': '2024-01-01',
            },
            {
                'country': 'LKA', 'rule_type': 'epf_employer', 'name': 'EPF Employer Contribution',
                'calculation': {'type': 'percentage', 'rate': 0.12},
                'effective_from': '2024-01-01',
            },
            {
                'country': 'LKA', 'rule_type': 'etf', 'name': 'ETF Employer Contribution',
                'calculation': {'type': 'percentage', 'rate': 0.03},
                'effective_from': '2024-01-01',
            },
            {
                'country': 'LKA', 'rule_type': 'income_tax', 'name': 'APIT - Tax Year 2024/25',
                'calculation': {
                    'type': 'slab',
                    'slabs': [
                        {'from': 0, 'to': 1200000, 'rate': 0},
                        {'from': 1200000, 'to': 1700000, 'rate': 6},
                        {'from': 1700000, 'to': 2200000, 'rate': 12},
                        {'from': 2200000, 'to': 2700000, 'rate': 18},
                        {'from': 2700000, 'to': 3200000, 'rate': 24},
                        {'from': 3200000, 'to': 3700000, 'rate': 30},
                        {'from': 3700000, 'to': None, 'rate': 36},
                    ],
                },
                'effective_from': '2024-04-01',
            },
        ]

        for r in rules:
            StatutoryRule.objects.get_or_create(
                country=r['country'], rule_type=r['rule_type'], name=r['name'],
                defaults={
                    'calculation': r['calculation'],
                    'effective_from': r['effective_from'],
                }
            )
        self.stdout.write(f'  ✓ {len(rules)} statutory rules created')

    def _seed_holiday_calendar(self, tenant):
        from leave_attendance.models import HolidayCalendar, Holiday

        cal, _ = HolidayCalendar.objects.get_or_create(
            tenant=tenant, name='Sri Lanka 2026', year=2026,
            defaults={'country': 'LKA'}
        )

        holidays_data = [
            ('Tamil Thai Pongal Day', '2026-01-14', 'public'),
            ('Duruthu Full Moon Poya', '2026-01-14', 'poya'),
            ('National Day', '2026-02-04', 'public'),
            ('Navam Full Moon Poya', '2026-02-12', 'poya'),
            ('Medin Full Moon Poya', '2026-03-14', 'poya'),
            ('Sinhala & Tamil New Year', '2026-04-13', 'public'),
            ('Sinhala & Tamil New Year', '2026-04-14', 'public'),
            ('Bak Full Moon Poya', '2026-04-12', 'poya'),
            ('May Day', '2026-05-01', 'public'),
            ('Vesak Full Moon Poya', '2026-05-12', 'poya'),
            ('Day after Vesak', '2026-05-13', 'public'),
            ('Poson Full Moon Poya', '2026-06-10', 'poya'),
            ('Esala Full Moon Poya', '2026-07-10', 'poya'),
            ('Nikini Full Moon Poya', '2026-08-08', 'poya'),
            ('Binara Full Moon Poya', '2026-09-07', 'poya'),
            ('Vap Full Moon Poya', '2026-10-06', 'poya'),
            ('Deepavali', '2026-10-20', 'public'),
            ('Il Full Moon Poya', '2026-11-05', 'poya'),
            ('Unduvap Full Moon Poya', '2026-12-04', 'poya'),
            ('Christmas Day', '2026-12-25', 'public'),
        ]

        for name, dt, typ in holidays_data:
            Holiday.objects.get_or_create(
                calendar=cal, date=dt,
                defaults={'name': name, 'type': typ}
            )
        self.stdout.write(f'  ✓ {len(holidays_data)} holidays in 2026 calendar')

    def _seed_onboarding_template(self, tenant):
        """Seed default 5-phase new-hire onboarding template."""
        try:
            from onboarding.models import OnboardingTemplate, OnboardingPhase, OnboardingTask
        except ImportError:
            self.stdout.write('  ⚠ onboarding models not available — skipping')
            return

        template, _ = OnboardingTemplate.objects.get_or_create(
            tenant=tenant,
            name='Standard New Hire',
            defaults={
                'description': 'Default 5-phase onboarding process for new employees',
                'is_default': True,
            }
        )

        phases = [
            {
                'name': 'Pre-Boarding', 'order': 1, 'offset_days': -5,
                'tasks': [
                    {'title': 'Send welcome email', 'assignee_type': 'hr', 'offset': -5},
                    {'title': 'Prepare workstation and equipment', 'assignee_type': 'it', 'offset': -3},
                    {'title': 'Create system accounts (email, Slack, VPN)', 'assignee_type': 'it', 'offset': -2},
                    {'title': 'Share first-day agenda', 'assignee_type': 'hr', 'offset': -1},
                ]
            },
            {
                'name': 'Day 1 — Orientation', 'order': 2, 'offset_days': 0,
                'tasks': [
                    {'title': 'Welcome meeting with HR', 'assignee_type': 'hr', 'offset': 0},
                    {'title': 'Office tour and team introductions', 'assignee_type': 'manager', 'offset': 0},
                    {'title': 'Issue ID card and access badge', 'assignee_type': 'hr', 'offset': 0},
                    {'title': 'Review employee handbook', 'assignee_type': 'employee', 'offset': 1},
                    {'title': 'Complete I-9 / NIC verification', 'assignee_type': 'hr', 'offset': 0},
                ]
            },
            {
                'name': 'Week 1', 'order': 3, 'offset_days': 1,
                'tasks': [
                    {'title': 'Meet with direct manager', 'assignee_type': 'manager', 'offset': 1},
                    {'title': 'Complete mandatory compliance training', 'assignee_type': 'employee', 'offset': 5},
                    {'title': 'Set up payroll bank details', 'assignee_type': 'employee', 'offset': 3},
                    {'title': 'Sign employment contract', 'assignee_type': 'employee', 'offset': 1},
                    {'title': 'Enrol in benefits', 'assignee_type': 'employee', 'offset': 5},
                ]
            },
            {
                'name': 'Month 1', 'order': 4, 'offset_days': 7,
                'tasks': [
                    {'title': '30-day check-in with manager', 'assignee_type': 'manager', 'offset': 30},
                    {'title': 'Complete department-specific training', 'assignee_type': 'employee', 'offset': 25},
                    {'title': 'Set 90-day goals with manager', 'assignee_type': 'manager', 'offset': 28},
                    {'title': 'HR pulse check-in', 'assignee_type': 'hr', 'offset': 30},
                ]
            },
            {
                'name': 'Probation End', 'order': 5, 'offset_days': 84,
                'tasks': [
                    {'title': 'Probation review with manager', 'assignee_type': 'manager', 'offset': 84},
                    {'title': 'HR probation confirmation letter', 'assignee_type': 'hr', 'offset': 85},
                    {'title': 'Update employment status to confirmed', 'assignee_type': 'hr', 'offset': 85},
                ]
            },
        ]

        for phase_data in phases:
            phase, _ = OnboardingPhase.objects.get_or_create(
                template=template,
                name=phase_data['name'],
                defaults={'order': phase_data['order'], 'start_offset_days': phase_data['offset_days']},
            )
            for task_data in phase_data['tasks']:
                OnboardingTask.objects.get_or_create(
                    phase=phase,
                    title=task_data['title'],
                    defaults={
                        'assignee_type': task_data['assignee_type'],
                        'due_offset_days': task_data['offset'],
                    }
                )

        self.stdout.write(f'  ✓ Default onboarding template seeded ({len(phases)} phases)')

    def _seed_email_templates(self, tenant):
        """Seed standard HRM email templates."""
        try:
            from platform_core.models import EmailTemplate
        except ImportError:
            self.stdout.write('  ⚠ EmailTemplate model not available — skipping')
            return

        templates = [
            {
                'slug': 'new_hire_welcome',
                'name': 'New Hire Welcome',
                'subject': 'Welcome to {{company_name}}, {{employee_first_name}}!',
                'body': (
                    'Dear {{employee_first_name}},\n\n'
                    'Welcome to {{company_name}}! We are thrilled to have you join our team.\n\n'
                    'Your start date is {{start_date}}. Please report to {{reporting_location}} '
                    'at {{start_time}}.\n\n'
                    'Your manager is {{manager_name}} ({{manager_email}}).\n\n'
                    'If you have any questions before your start date, please don\'t hesitate to '
                    'reach out to HR at {{hr_email}}.\n\n'
                    'Looking forward to seeing you!\n\nBest regards,\n{{hr_contact_name}}\nHR Team'
                ),
                'category': 'onboarding',
            },
            {
                'slug': 'leave_approved',
                'name': 'Leave Request Approved',
                'subject': 'Leave Request Approved — {{leave_type}} ({{start_date}} to {{end_date}})',
                'body': (
                    'Dear {{employee_first_name}},\n\n'
                    'Your {{leave_type}} request for {{total_days}} day(s) from {{start_date}} '
                    'to {{end_date}} has been approved by {{approver_name}}.\n\n'
                    'Remaining {{leave_type}} balance: {{remaining_balance}} days.\n\n'
                    'Best regards,\nHR Team'
                ),
                'category': 'leave',
            },
            {
                'slug': 'leave_rejected',
                'name': 'Leave Request Rejected',
                'subject': 'Leave Request Not Approved — {{leave_type}} ({{start_date}})',
                'body': (
                    'Dear {{employee_first_name}},\n\n'
                    'Your {{leave_type}} request for {{start_date}} to {{end_date}} '
                    'could not be approved.\n\n'
                    'Reason: {{rejection_reason}}\n\n'
                    'If you have questions, please contact your manager or HR.\n\n'
                    'Best regards,\nHR Team'
                ),
                'category': 'leave',
            },
            {
                'slug': 'payslip_available',
                'name': 'Payslip Available',
                'subject': 'Your payslip for {{pay_period}} is now available',
                'body': (
                    'Dear {{employee_first_name}},\n\n'
                    'Your payslip for {{pay_period}} is now available in the HRM portal.\n\n'
                    'Log in at {{portal_url}} to view and download your payslip.\n\n'
                    'Best regards,\nPayroll Team'
                ),
                'category': 'payroll',
            },
            {
                'slug': 'probation_review_reminder',
                'name': 'Probation Review Reminder',
                'subject': 'Probation review for {{employee_full_name}} — {{review_date}}',
                'body': (
                    'Dear {{manager_first_name}},\n\n'
                    'This is a reminder that {{employee_full_name}}\'s probation review is due '
                    'on {{review_date}}.\n\n'
                    'Please complete the performance review form in the HRM portal before the '
                    'review date.\n\n'
                    'Log in at {{portal_url}}/performance/reviews to submit your assessment.\n\n'
                    'Best regards,\nHR Team'
                ),
                'category': 'performance',
            },
            {
                'slug': 'contract_expiry_warning',
                'name': 'Employment Contract Expiry Warning',
                'subject': '⚠ Contract expiring in {{days_remaining}} days — {{employee_full_name}}',
                'body': (
                    'Dear {{hr_contact_name}},\n\n'
                    '{{employee_full_name}}\'s employment contract is due to expire on '
                    '{{expiry_date}} ({{days_remaining}} days remaining).\n\n'
                    'Please review and take appropriate action at {{portal_url}}.\n\n'
                    'Best regards,\nConnectHR Automated Notifications'
                ),
                'category': 'hr_alert',
            },
            {
                'slug': 'birthday_greeting',
                'name': 'Birthday Greeting',
                'subject': 'Happy Birthday, {{employee_first_name}}! 🎂',
                'body': (
                    'Dear {{employee_first_name}},\n\n'
                    'Wishing you a very Happy Birthday from everyone at {{company_name}}!\n\n'
                    'We hope you have a wonderful day.\n\n'
                    'Best wishes,\n{{company_name}} Team'
                ),
                'category': 'engagement',
            },
            {
                'slug': 'document_expiry_warning',
                'name': 'Document Expiry Warning',
                'subject': '⚠ {{document_type}} expiring soon — {{employee_full_name}}',
                'body': (
                    'Dear {{employee_first_name}},\n\n'
                    'Your {{document_type}} ({{document_id}}) is expiring on {{expiry_date}} '
                    '({{days_remaining}} days remaining).\n\n'
                    'Please renew it and upload the updated document at {{portal_url}}.\n\n'
                    'Best regards,\nHR Team'
                ),
                'category': 'hr_alert',
            },
        ]

        created = 0
        for tmpl in templates:
            _, was_created = EmailTemplate.objects.get_or_create(
                tenant=tenant,
                slug=tmpl['slug'],
                defaults={
                    'name': tmpl['name'],
                    'subject': tmpl['subject'],
                    'body': tmpl['body'],
                    'category': tmpl['category'],
                }
            )
            if was_created:
                created += 1

        self.stdout.write(f'  ✓ Email templates: {created} created, {len(templates) - created} already existed')

    def _seed_workflow_templates(self, tenant):
        """Seed default HRM workflow automation templates."""
        try:
            from workflows.models import WorkflowDefinition
        except ImportError:
            self.stdout.write('  ⚠ WorkflowDefinition model not available — skipping')
            return

        templates = [
            {
                'name': 'New Hire Welcome Email',
                'trigger_type': 'employee_created',
                'description': 'Automatically send welcome email when a new employee is created',
                'actions': [
                    {
                        'type': 'send_email',
                        'template_slug': 'new_hire_welcome',
                        'delay_hours': 0,
                        'recipient': 'employee',
                    }
                ],
                'is_active': True,
            },
            {
                'name': 'Leave Auto-Approve Under 1 Day',
                'trigger_type': 'leave_requested',
                'description': 'Automatically approve casual leave requests of 0.5 or 1 day',
                'conditions': [
                    {
                        'field': 'leave_type',
                        'operator': 'equals',
                        'value': 'CL',
                    },
                    {
                        'field': 'total_days',
                        'operator': 'lte',
                        'value': 1,
                    }
                ],
                'actions': [
                    {
                        'type': 'update_field',
                        'entity': 'leave_request',
                        'field': 'status',
                        'value': 'approved',
                        'delay_hours': 0,
                    }
                ],
                'is_active': True,
            },
            {
                'name': 'Birthday Greeting',
                'trigger_type': 'employee_birthday',
                'description': 'Send birthday greeting to employee on their birthday',
                'actions': [
                    {
                        'type': 'send_email',
                        'template_slug': 'birthday_greeting',
                        'delay_hours': 0,
                        'recipient': 'employee',
                    }
                ],
                'is_active': True,
            },
            {
                'name': 'Contract Expiry 30-Day Warning',
                'trigger_type': 'contract_expiry_30d',
                'description': 'Alert HR 30 days before an employment contract expires',
                'actions': [
                    {
                        'type': 'send_email',
                        'template_slug': 'contract_expiry_warning',
                        'delay_hours': 0,
                        'recipient': 'hr',
                    },
                    {
                        'type': 'create_task',
                        'title': 'Review contract renewal for {{employee_full_name}}',
                        'assignee_type': 'hr',
                        'due_offset_days': 14,
                    }
                ],
                'is_active': True,
            },
            {
                'name': 'Probation Due Reminder',
                'trigger_type': 'probation_due_7d',
                'description': 'Remind manager to complete probation review 7 days before due date',
                'actions': [
                    {
                        'type': 'send_email',
                        'template_slug': 'probation_review_reminder',
                        'delay_hours': 0,
                        'recipient': 'manager',
                    }
                ],
                'is_active': True,
            },
        ]

        created = 0
        for wf in templates:
            _, was_created = WorkflowDefinition.objects.get_or_create(
                tenant=tenant,
                name=wf['name'],
                defaults={
                    'trigger_type': wf['trigger_type'],
                    'description': wf['description'],
                    'conditions': wf.get('conditions', []),
                    'actions': wf['actions'],
                    'is_active': wf['is_active'],
                    'is_template': True,
                }
            )
            if was_created:
                created += 1

        self.stdout.write(f'  ✓ Workflow templates: {created} created, {len(templates) - created} already existed')

