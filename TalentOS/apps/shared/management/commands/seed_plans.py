"""Seed Plan objects for ATS subscription system."""
from django.core.management.base import BaseCommand

PLANS = [
    {
        'tier': 'free_trial',
        'name': 'Free Trial',
        'price_monthly': '0.00',
        'price_annually': '0.00',
        'max_jobs': 3,
        'max_candidates': 50,
        'max_users': 2,
        'features': {'analytics': False, 'api_access': False, 'integrations': False},
    },
    {
        'tier': 'starter',
        'name': 'Starter',
        'price_monthly': '49.00',
        'price_annually': '490.00',
        'max_jobs': 10,
        'max_candidates': 500,
        'max_users': 5,
        'features': {'analytics': True, 'api_access': False, 'integrations': False},
    },
    {
        'tier': 'professional',
        'name': 'Professional',
        'price_monthly': '149.00',
        'price_annually': '1490.00',
        'max_jobs': 50,
        'max_candidates': 5000,
        'max_users': 20,
        'features': {'analytics': True, 'api_access': True, 'integrations': True},
    },
    {
        'tier': 'enterprise',
        'name': 'Enterprise',
        'price_monthly': '499.00',
        'price_annually': '4990.00',
        'max_jobs': -1,
        'max_candidates': -1,
        'max_users': -1,
        'features': {
            'analytics': True,
            'api_access': True,
            'integrations': True,
            'sso': True,
            'dedicated_support': True,
        },
    },
]


class Command(BaseCommand):
    help = 'Seed ATS subscription plans'

    def handle(self, *args, **options):
        from apps.accounts.models import Plan
        created = 0
        for data in PLANS:
            _, c = Plan.objects.update_or_create(tier=data['tier'], defaults=data)
            if c:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f'Plans: {created} created, {len(PLANS) - created} updated'
            )
        )
