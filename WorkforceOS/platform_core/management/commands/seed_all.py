"""Master seed command for HRM System — runs all seed commands in order."""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Seed all HRM reference data: roles, leave types, tax brackets, email templates, holidays.'

    COMMANDS = [
        ('seed_hrm_roles',        'HRM roles & permissions'),
        ('seed_leave_types',      'Leave type catalog'),
        ('seed_holidays',         'Public holidays (LK)'),
        ('seed_apit_brackets',    'APIT tax brackets'),
        ('seed_hrm_templates',    'Email / notification templates'),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant', dest='tenant_id', default=None,
            help='Only seed for this tenant ID (UUID). Defaults to all tenants.'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be seeded without making changes.'
        )

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        dry_run   = options.get('dry_run')

        self.stdout.write(self.style.MIGRATE_HEADING('HRM — Running all seed commands'))
        if dry_run:
            self.stdout.write(self.style.WARNING('  [DRY RUN — no changes will be made]'))

        kwargs = {}
        if tenant_id:
            kwargs['tenant'] = tenant_id
        if dry_run:
            kwargs['dry_run'] = True

        errors = []
        for cmd, description in self.COMMANDS:
            self.stdout.write(f'  → {description}... ', ending='')
            self.stdout.flush()
            if not dry_run:
                try:
                    call_command(cmd, **{k: v for k, v in kwargs.items()
                                         if k in self._get_cmd_args(cmd)},
                                 verbosity=0, stdout=self.stdout, stderr=self.stderr)
                    self.stdout.write(self.style.SUCCESS('OK'))
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f'FAILED: {exc}'))
                    errors.append((cmd, str(exc)))
            else:
                self.stdout.write(self.style.WARNING('(skipped — dry run)'))

        self.stdout.write('')
        if errors:
            self.stdout.write(self.style.ERROR(f'{len(errors)} command(s) failed:'))
            for cmd, err in errors:
                self.stdout.write(f'  • {cmd}: {err}')
        else:
            self.stdout.write(self.style.SUCCESS('All HRM seed commands completed successfully!'))

    @staticmethod
    def _get_cmd_args(cmd_name):
        """Return known extra kwargs for each command."""
        mapping = {
            'seed_hrm_roles': ['tenant'],
            'seed_leave_types': ['tenant'],
            'seed_holidays': ['tenant', 'year'],
            'seed_apit_brackets': [],
            'seed_hrm_templates': ['tenant'],
        }
        return mapping.get(cmd_name, [])
