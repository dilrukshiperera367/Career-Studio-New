"""Seed HRM RBAC roles and permissions."""
from django.core.management.base import BaseCommand

HRM_ROLES = [
    {
        'name': 'Super Admin',
        'description': 'Full platform access',
        'permissions': ['*'],
    },
    {
        'name': 'HR Admin',
        'description': 'Full HR module access',
        'permissions': ['employees.manage', 'payroll.run', 'payroll.view', 'leave.approve', 'attendance.manage', 'reports.view', 'settings.manage'],
    },
    {
        'name': 'HR Officer',
        'description': 'Day-to-day HR operations',
        'permissions': ['employees.manage', 'payroll.view', 'leave.approve', 'attendance.manage', 'reports.view'],
    },
    {
        'name': 'Manager',
        'description': 'Team management access',
        'permissions': ['employees.view', 'leave.approve', 'attendance.view', 'reports.view_team'],
    },
    {
        'name': 'Employee',
        'description': 'Self-service access',
        'permissions': ['self.view', 'self.leave_apply', 'self.attendance_clock', 'self.payslip'],
    },
    {
        'name': 'Viewer',
        'description': 'Read-only access',
        'permissions': ['employees.view', 'reports.view'],
    },
]

HRM_PERMISSIONS = [
    'employees.manage', 'employees.view',
    'payroll.run', 'payroll.view', 'payroll.approve',
    'leave.approve', 'leave.view',
    'attendance.manage', 'attendance.view',
    'reports.view', 'reports.view_team', 'reports.export',
    'settings.manage', 'settings.users', 'settings.roles',
    'self.view', 'self.leave_apply', 'self.attendance_clock', 'self.payslip',
    'onboarding.manage', 'performance.manage', 'performance.view',
    'helpdesk.manage', 'helpdesk.view',
    'engagement.manage',
]


class Command(BaseCommand):
    help = 'Seed HRM RBAC roles and permissions'

    def handle(self, *args, **options):
        try:
            from authentication.models import Role
        except ImportError:
            self.stdout.write(self.style.WARNING('Role model not found in authentication — skipping'))
            return

        created = 0
        for role_data in HRM_ROLES:
            _, was_created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults={
                    'description': role_data['description'],
                    'permissions': role_data['permissions'],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {created} HRM roles'))
