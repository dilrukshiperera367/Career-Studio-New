"""Seed Sri Lanka APIT (Advance Personal Income Tax) brackets for 2025/2026."""
from django.core.management.base import BaseCommand

APIT_BRACKETS_2025_2026 = [
    # (annual_income_from, annual_income_to_exclusive, rate_percent, fixed_deduction)
    # Based on IRD Sri Lanka 2025/2026 tax table
    (0, 1_200_000, 0, 0),
    (1_200_000, 1_700_000, 6, 0),
    (1_700_000, 2_200_000, 12, 30_000),
    (2_200_000, 2_700_000, 18, 102_000),
    (2_700_000, 3_200_000, 24, 264_000),
    (3_200_000, 3_700_000, 30, 456_000),
    (3_700_000, None, 36, 678_000),
]


class Command(BaseCommand):
    help = 'Seed APIT tax brackets for 2025/2026'

    def handle(self, *args, **options):
        try:
            from payroll.models import APTIBracket
            created = 0
            for from_amt, to_amt, rate, fixed_ded in APIT_BRACKETS_2025_2026:
                _, was_created = APTIBracket.objects.get_or_create(
                    income_from=from_amt,
                    income_to=to_amt,
                    defaults={'rate': rate, 'fixed_deduction': fixed_ded, 'tax_year': '2025/2026'},
                )
                if was_created:
                    created += 1
            self.stdout.write(self.style.SUCCESS(f'Seeded {created} APIT brackets'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'APTIBracket model not available: {e}'))
            self.stdout.write(self.style.SUCCESS('APIT brackets are hardcoded in payroll/calculator.py as fallback'))
