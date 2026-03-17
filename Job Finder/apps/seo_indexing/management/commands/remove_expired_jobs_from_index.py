"""
Management command: remove_expired_jobs_from_index

Finds all job listings that are expired or closed, marks their SitemapEntry
as is_expired=True, and calls Google Indexing API URL_DELETED.

Usage:
    python manage.py remove_expired_jobs_from_index
    python manage.py remove_expired_jobs_from_index --dry-run
"""
from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import JobListing
from apps.seo_indexing.models import SitemapEntry, CrawlHealthSnapshot


class Command(BaseCommand):
    help = "Remove expired/closed job pages from sitemap and notify Google to deindex them."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Expired = status not active OR expires_at in the past
        expired_qs = JobListing.objects.filter(
            status__in=["expired", "closed", "filled", "rejected"]
        ) | JobListing.objects.filter(
            expires_at__lt=timezone.now(),
            status="active",
        )

        expired_slugs = list(expired_qs.values_list("slug", flat=True).distinct())

        # Find sitemap entries that are still marked indexable
        indexable_expired = SitemapEntry.objects.filter(
            page_type="job",
            slug__in=expired_slugs,
            is_expired=False,
        )

        removed = 0
        api_successes = 0
        api_failures = 0

        for entry in indexable_expired:
            self.stdout.write(f"  {'[DRY]' if dry_run else ''} Removing: {entry.slug}")
            if not dry_run:
                entry.is_expired = True
                entry.is_indexable = False
                entry.save(update_fields=["is_expired", "is_indexable"])

                from apps.seo_indexing.indexing_api_client import notify_job_removed
                ok = notify_job_removed(entry.slug)
                if ok:
                    api_successes += 1
                else:
                    api_failures += 1
            removed += 1

        # Also auto-update status of active jobs that have passed expires_at
        if not dry_run:
            auto_expired = JobListing.objects.filter(
                expires_at__lt=timezone.now(), status="active"
            )
            count_ae = auto_expired.update(status="expired")
            if count_ae:
                self.stdout.write(f"Auto-expired {count_ae} job listings (status → expired).")

            # Update today's crawl health
            if removed:
                snap, _ = CrawlHealthSnapshot.objects.get_or_create(date=date.today())
                snap.total_expired_removed = (snap.total_expired_removed or 0) + removed
                snap.indexing_api_successes = (snap.indexing_api_successes or 0) + api_successes
                snap.indexing_api_failures = (snap.indexing_api_failures or 0) + api_failures
                active_total = SitemapEntry.objects.filter(is_indexable=True, is_expired=False).count()
                snap.total_indexed = active_total
                snap.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] ' if dry_run else ''}Removed {removed} expired job pages. "
                f"API: {api_successes} OK, {api_failures} failed."
            )
        )
