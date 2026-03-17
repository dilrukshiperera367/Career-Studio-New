"""Seed default pipeline stage templates."""
from django.core.management.base import BaseCommand

DEFAULT_STAGES = [
    {'name': 'Applied', 'stage_type': 'applied', 'order': 1, 'color': '#6B7280'},
    {'name': 'Screening', 'stage_type': 'screening', 'order': 2, 'color': '#3B82F6'},
    {'name': 'Interview', 'stage_type': 'interview', 'order': 3, 'color': '#8B5CF6'},
    {'name': 'Technical Assessment', 'stage_type': 'assessment', 'order': 4, 'color': '#F59E0B'},
    {'name': 'Offer', 'stage_type': 'offer', 'order': 5, 'color': '#10B981'},
    {'name': 'Hired', 'stage_type': 'hired', 'order': 6, 'color': '#059669'},
    {'name': 'Rejected', 'stage_type': 'rejected', 'order': 99, 'color': '#EF4444'},
]


class Command(BaseCommand):
    help = 'Seed default pipeline stage templates'

    def handle(self, *args, **options):
        try:
            from apps.jobs.models import PipelineStageTemplate
            created = 0
            for stage in DEFAULT_STAGES:
                _, was_created = PipelineStageTemplate.objects.get_or_create(
                    name=stage['name'],
                    defaults=stage,
                )
                if was_created:
                    created += 1
            self.stdout.write(self.style.SUCCESS(f'Seeded {created} pipeline stage templates'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'PipelineStageTemplate not available: {e}'))
