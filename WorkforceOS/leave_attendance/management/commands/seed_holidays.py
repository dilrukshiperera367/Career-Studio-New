"""Seed Sri Lanka public holidays for 2026."""
from django.core.management.base import BaseCommand

HOLIDAYS_2026 = [
    ('2026-01-01', "New Year's Day", False),
    ('2026-01-14', 'Thai Pongal', False),
    ('2026-02-04', 'Independence Day', False),
    ('2026-02-17', 'Maha Sivarathri Day', False),
    ('2026-03-30', 'Id ul-Fitr (Ramazan Festival)', False),
    ('2026-04-13', 'Day before Sinhala & Tamil New Year', False),
    ('2026-04-14', 'Sinhala & Tamil New Year', False),
    ('2026-04-21', 'Good Tuesday - Day before Vesak', False),
    ('2026-05-01', 'May Day', False),
    ('2026-05-22', 'Vesak Full Moon Poya Day', False),
    ('2026-05-23', 'Day following Vesak Full Moon Poya', False),
    ('2026-06-06', 'Id ul-Alha (Hadj Festival)', False),
    ('2026-06-19', 'Poson Full Moon Poya Day', False),
    ('2026-09-05', 'Milad un-Nabi - Birth of Prophet Mohamed', False),
    ('2026-10-01', 'Thai Pongal / Deepavali', False),
    ('2026-12-25', 'Christmas Day', False),
    # Monthly Poya days
    ('2026-01-23', 'Duruthu Full Moon Poya', True),
    ('2026-02-21', 'Navam Full Moon Poya', True),
    ('2026-03-23', 'Medin Full Moon Poya', True),
    ('2026-04-22', 'Bak Full Moon Poya', True),
    ('2026-07-18', 'Esala Full Moon Poya', True),
    ('2026-08-17', 'Nikini Full Moon Poya', True),
    ('2026-09-15', 'Binara Full Moon Poya', True),
    ('2026-10-14', 'Vap Full Moon Poya', True),
    ('2026-11-12', "Il Full Moon Poya", True),
    ('2026-12-12', 'Unduwap Full Moon Poya', True),
]


class Command(BaseCommand):
    help = 'Seed Sri Lanka public holidays 2026'

    def handle(self, *args, **options):
        from datetime import date
        try:
            from leave_attendance.models import Holiday
        except ImportError:
            self.stdout.write(self.style.WARNING('Holiday model not found — skipping'))
            return

        created = 0
        for date_str, name, is_optional in HOLIDAYS_2026:
            year, month, day = map(int, date_str.split('-'))
            _, was_created = Holiday.objects.get_or_create(
                date=date(year, month, day),
                defaults={'name': name, 'is_optional': is_optional},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {created} holidays for 2026'))
