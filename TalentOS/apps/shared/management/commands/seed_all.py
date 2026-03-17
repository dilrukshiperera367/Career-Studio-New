"""
Master seed command for ATS System.
Run: python manage.py seed_all
Seeds: permissions, pipeline templates, email templates, consent version, taxonomy basics
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run all ATS seed commands in the correct order'

    def add_arguments(self, parser):
        parser.add_argument('--fresh', action='store_true', help='Clear existing seed data before re-seeding')

    def handle(self, *args, **options):
        steps = [
            ('seed_permissions', 'Seeding permission codenames'),
            ('seed_email_templates', 'Seeding email templates'),
            ('seed_pipeline_templates', 'Seeding pipeline stage templates'),
        ]
        
        # Try optional taxonomy seed
        try:
            from apps.taxonomy.models import Skill
            steps.append(('seed_taxonomy', 'Seeding skill taxonomy'))
        except Exception:
            pass

        for cmd, label in steps:
            self.stdout.write(f'\n→ {label}...')
            try:
                call_command(cmd, verbosity=0)
                self.stdout.write(self.style.SUCCESS(f'  ✓ {label}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠ {cmd} skipped: {e}'))

        self.stdout.write(self.style.SUCCESS('\n✅ ATS seed complete'))
