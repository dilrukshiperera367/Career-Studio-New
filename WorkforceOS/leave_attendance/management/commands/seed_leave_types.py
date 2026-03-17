"""Seed standard Sri Lanka leave types."""
from django.core.management.base import BaseCommand

LEAVE_TYPES = [
    {'name': 'Annual Leave', 'code': 'AL', 'max_days_per_year': 14, 'is_paid': True, 'carry_forward_days': 7, 'accrual_type': 'annual'},
    {'name': 'Casual Leave', 'code': 'CL', 'max_days_per_year': 7, 'is_paid': True, 'carry_forward_days': 0, 'accrual_type': 'annual'},
    {'name': 'Sick Leave', 'code': 'SL', 'max_days_per_year': 7, 'is_paid': True, 'carry_forward_days': 0, 'accrual_type': 'annual'},
    {'name': 'Maternity Leave', 'code': 'ML', 'max_days_per_year': 84, 'is_paid': True, 'carry_forward_days': 0, 'accrual_type': 'none'},
    {'name': 'Paternity Leave', 'code': 'PL', 'max_days_per_year': 3, 'is_paid': True, 'carry_forward_days': 0, 'accrual_type': 'none'},
    {'name': 'No-Pay Leave', 'code': 'NP', 'max_days_per_year': 365, 'is_paid': False, 'carry_forward_days': 0, 'accrual_type': 'none'},
    {'name': 'Short Leave', 'code': 'SHL', 'max_days_per_year': 10, 'is_paid': True, 'carry_forward_days': 0, 'accrual_type': 'annual'},
    {'name': 'Comp-Off', 'code': 'CO', 'max_days_per_year': 30, 'is_paid': True, 'carry_forward_days': 5, 'accrual_type': 'earned'},
]


class Command(BaseCommand):
    help = 'Seed standard Sri Lanka leave types'

    def handle(self, *args, **options):
        try:
            from leave_attendance.models import LeaveType
        except ImportError:
            self.stdout.write(self.style.WARNING('LeaveType model not found — skipping'))
            return

        created = 0
        for lt in LEAVE_TYPES:
            defaults = {k: v for k, v in lt.items() if k != 'code'}
            _, was_created = LeaveType.objects.get_or_create(
                name=lt['name'],
                defaults=defaults,
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {created} leave types'))
