"""
Management command: rebuild_sitemap

Scans all active jobs, companies, categories, districts, and salary pages,
syncs SitemapEntry records, and writes a sitemap index file.

Usage:
    python manage.py rebuild_sitemap
    python manage.py rebuild_sitemap --notify-google   # also calls Indexing API for new pages
    python manage.py rebuild_sitemap --type job        # rebuild one page type only
"""
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.jobs.models import JobListing
from apps.employers.models import EmployerAccount
from apps.taxonomy.models import JobCategory, District
from apps.seo_indexing.models import SitemapEntry, CrawlHealthSnapshot

SITE_URL = "https://jobfinder.lk"
LOCALES = ["en", "si", "ta"]


def upsert(page_type, slug, rel_path, priority, freq):
    url = f"{SITE_URL}/en/{rel_path}"
    obj, created = SitemapEntry.objects.update_or_create(
        page_type=page_type, slug=slug,
        defaults={
            "url": url,
            "priority": priority,
            "change_frequency": freq,
            "is_indexable": True,
            "is_expired": False,
        },
    )
    return created


class Command(BaseCommand):
    help = "Rebuild sitemap entries from live data and optionally notify Google Indexing API."

    def add_arguments(self, parser):
        parser.add_argument("--notify-google", action="store_true", help="Send URL_UPDATED to Indexing API for new entries")
        parser.add_argument("--type", choices=["job", "company", "category", "city", "salary"], help="Rebuild only this page type")

    def handle(self, *args, **options):
        do_type = options.get("type")
        notify = options["notify_google"]
        new_count = 0
        expired_count = 0

        # ── Jobs ──────────────────────────────────────────────────────────
        if not do_type or do_type == "job":
            active_slugs = set()
            for job in JobListing.objects.filter(status="active").values("slug"):
                slug = job["slug"]
                active_slugs.add(slug)
                created = upsert("job", slug, f"jobs/{slug}", 0.9, "daily")
                if created:
                    new_count += 1
                    if notify:
                        from apps.seo_indexing.indexing_api_client import notify_job_published
                        notify_job_published(slug)

            # Mark expired
            expired = SitemapEntry.objects.filter(page_type="job", is_expired=False).exclude(slug__in=active_slugs)
            for entry in expired:
                entry.is_expired = True
                entry.is_indexable = False
                entry.save(update_fields=["is_expired", "is_indexable"])
                expired_count += 1
                if notify:
                    from apps.seo_indexing.indexing_api_client import notify_job_removed
                    notify_job_removed(entry.slug)
            self.stdout.write(f"Jobs: {len(active_slugs)} active, {expired_count} expired")

        # ── Companies ────────────────────────────────────────────────────
        if not do_type or do_type == "company":
            for emp in EmployerAccount.objects.values("slug"):
                slug = emp["slug"]
                created = upsert("company", slug, f"companies/{slug}", 0.7, "weekly")
                if created:
                    new_count += 1
            self.stdout.write(f"Companies: {EmployerAccount.objects.count()} synced")

        # ── Categories ───────────────────────────────────────────────────
        if not do_type or do_type == "category":
            for cat in JobCategory.objects.values("slug"):
                slug = cat["slug"]
                created = upsert("category", slug, f"jobs/category/{slug}", 0.8, "daily")
                if created:
                    new_count += 1
            self.stdout.write(f"Categories: {JobCategory.objects.count()} synced")

        # ── Cities ───────────────────────────────────────────────────────
        if not do_type or do_type == "city":
            for district in District.objects.values("slug"):
                slug = district["slug"]
                created = upsert("city", slug, f"jobs/city/{slug}", 0.75, "daily")
                if created:
                    new_count += 1
            self.stdout.write(f"Cities: {District.objects.count()} synced")

        # ── Salary pages ─────────────────────────────────────────────────
        if not do_type or do_type == "salary":
            for cat in JobCategory.objects.values("slug", "name_en"):
                slug = f"salary-{cat['slug']}"
                created = upsert("salary", slug, f"salary-guide/{cat['slug']}", 0.6, "weekly")
                if created:
                    new_count += 1

        # ── Update crawl health snapshot ─────────────────────────────────
        total = SitemapEntry.objects.filter(is_indexable=True, is_expired=False).count()
        CrawlHealthSnapshot.objects.update_or_create(
            date=date.today(),
            defaults={
                "total_indexed": total,
                "total_expired_removed": expired_count,
                "total_new_added": new_count,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Sitemap rebuild complete: {total} indexable, {new_count} new, {expired_count} expired"
            )
        )
