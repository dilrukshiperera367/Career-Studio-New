"""Management command: compute trending employer scores weekly."""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from apps.jobs.models import JobListing
from apps.employers.models import EmployerAccount
from apps.marketplace_search.models import TrendingEmployer


class Command(BaseCommand):
    help = "Compute weekly trending employer scores and save TrendingEmployer records."

    def handle(self, *args, **options):
        week_start = date.today() - timedelta(days=date.today().weekday())
        prev_week_start = week_start - timedelta(weeks=1)

        this_week_cutoff = timezone.now() - timedelta(days=7)
        prev_week_cutoff = timezone.now() - timedelta(days=14)

        # Jobs posted this week per employer
        this_week = (
            JobListing.objects.filter(published_at__gte=this_week_cutoff)
            .values("employer")
            .annotate(job_count=Count("id"))
        )
        prev_week = (
            JobListing.objects.filter(
                published_at__gte=prev_week_cutoff,
                published_at__lt=this_week_cutoff
            )
            .values("employer")
            .annotate(job_count=Count("id"))
        )

        this_week_map = {e["employer"]: e["job_count"] for e in this_week}
        prev_week_map = {e["employer"]: e["job_count"] for e in prev_week}

        # Compute view growth
        from apps.jobs.models import JobView
        this_week_views = (
            JobView.objects.filter(viewed_at__gte=this_week_cutoff)
            .values("job__employer")
            .annotate(views=Count("id"))
        )
        prev_week_views = (
            JobView.objects.filter(
                viewed_at__gte=prev_week_cutoff,
                viewed_at__lt=this_week_cutoff,
            )
            .values("job__employer")
            .annotate(views=Count("id"))
        )
        this_views_map = {v["job__employer"]: v["views"] for v in this_week_views}
        prev_views_map = {v["job__employer"]: v["views"] for v in prev_week_views}

        created = 0
        for employer_id, this_count in this_week_map.items():
            try:
                employer = EmployerAccount.objects.get(pk=employer_id)
            except EmployerAccount.DoesNotExist:
                continue

            prev_count = prev_week_map.get(employer_id, 0)
            velocity = this_count
            job_growth_pct = (
                ((this_count - prev_count) / max(prev_count, 1)) * 100
                if prev_count else 100.0
            )

            this_views = this_views_map.get(employer_id, 0)
            prev_views = prev_views_map.get(employer_id, 1)
            view_growth_pct = ((this_views - prev_views) / max(prev_views, 1)) * 100

            trending_score = (velocity * 5) + (view_growth_pct * 0.2) + (job_growth_pct * 0.1)

            reasons = []
            if velocity >= 3:
                reasons.append(f"Posted {velocity} new jobs this week")
            if view_growth_pct >= 50:
                reasons.append(f"{view_growth_pct:.0f}% more profile views")
            if not reasons:
                reasons.append("Actively hiring this week")

            TrendingEmployer.objects.update_or_create(
                employer=employer, week_start=week_start,
                defaults={
                    "job_post_velocity": velocity,
                    "view_growth_pct": view_growth_pct,
                    "application_growth_pct": job_growth_pct,
                    "trending_score": round(trending_score, 2),
                    "reasons": reasons,
                },
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Trending employers computed: {created} records for week {week_start}"
            )
        )
