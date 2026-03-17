"""
Management command to seed all ATS permission codenames.
Run: python manage.py seed_permissions
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


PERMISSION_CODENAMES = [
    # Jobs
    ('jobs.view', 'Can view jobs'),
    ('jobs.create', 'Can create jobs'),
    ('jobs.edit', 'Can edit jobs'),
    ('jobs.delete', 'Can delete jobs'),
    ('jobs.publish', 'Can publish jobs'),
    ('jobs.close', 'Can close jobs'),
    # Candidates
    ('candidates.view', 'Can view candidates'),
    ('candidates.create', 'Can create candidates'),
    ('candidates.edit', 'Can edit candidates'),
    ('candidates.delete', 'Can delete candidates'),
    ('candidates.export', 'Can export candidates'),
    ('candidates.import', 'Can import candidates'),
    ('candidates.merge', 'Can merge candidates'),
    # Applications
    ('applications.view', 'Can view applications'),
    ('applications.move_stage', 'Can move applications between stages'),
    ('applications.reject', 'Can reject applications'),
    ('applications.assign', 'Can assign applications to recruiters'),
    # Interviews
    ('interviews.view', 'Can view interviews'),
    ('interviews.create', 'Can schedule interviews'),
    ('interviews.edit', 'Can edit interviews'),
    ('interviews.score', 'Can submit scorecards'),
    # Offers
    ('offers.view', 'Can view offers'),
    ('offers.create', 'Can create offers'),
    ('offers.send', 'Can send offers'),
    ('offers.approve', 'Can approve offers'),
    # Reports
    ('reports.view', 'Can view reports'),
    ('reports.export', 'Can export reports'),
    # Settings
    ('settings.manage', 'Can manage settings'),
    ('settings.users', 'Can manage users'),
    ('settings.roles', 'Can manage roles'),
    ('settings.billing', 'Can manage billing'),
    # Workflows
    ('workflows.view', 'Can view workflows'),
    ('workflows.manage', 'Can manage workflow automations'),
    # Audit
    ('audit.view', 'Can view audit logs'),
]


class Command(BaseCommand):
    help = 'Seed all ATS permission codenames into the database'

    def handle(self, *args, **options):
        from django.apps import apps
        # Use a generic content type for custom permissions
        try:
            from apps.accounts.models import User
            ct = ContentType.objects.get_for_model(User)
        except Exception:
            ct = ContentType.objects.first()

        created = 0
        for codename, name in PERMISSION_CODENAMES:
            _, was_created = Permission.objects.get_or_create(
                codename=codename,
                content_type=ct,
                defaults={'name': name},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created} new permissions ({len(PERMISSION_CODENAMES)} total)'
        ))
